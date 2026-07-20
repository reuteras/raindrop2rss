#!/usr/bin/env python
"""Create rss feed for links saved to raindrop.io."""

import argparse
import configparser
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, NoReturn

import requests
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from pydantic import HttpUrl
from raindropiopy import API, Collection, CollectionRef, Raindrop
from requests.exceptions import ConnectionError, HTTPError, RequestException

import feedgen_atom_patch

feedgen_atom_patch.apply()


def read_configuration(config_file: str) -> configparser.RawConfigParser:
    """Read configuration file."""
    config: configparser.RawConfigParser = configparser.RawConfigParser()
    config.read(filenames=config_file)
    if not config.sections():
        print("Can't find configuration file.")
        sys.exit(1)
    return config


DEFAULT_IMAGE_MIME_TYPE = "image/jpeg"


def get_image_mime_type(url: str) -> str | None:
    """Determine an image's real mime type from the server's Content-Type header.

    The URL's file extension can't be trusted (e.g. a raindrop cover URL
    ending in .pdf can actually serve a .webp image), so this inspects the
    HTTP response instead. Tries HEAD first and falls back to GET since some
    servers don't return Content-Type on HEAD requests.
    """
    for method in (requests.head, requests.get):
        kwargs = {"allow_redirects": True, "timeout": 10}
        if method is requests.get:
            kwargs["stream"] = True
        try:
            response = method(url, **kwargs)
            with response:
                if response.ok:
                    content_type = (
                        response.headers.get("Content-Type", "").split(";")[0].strip()
                    )
                    if content_type.startswith("image/"):
                        return content_type
        except RequestException:
            continue
    return None


def init_db(arguments) -> sqlite3.Connection:
    """Init SQLite3 database for articles."""
    try:
        con: sqlite3.Connection = sqlite3.connect(database=arguments.db_path)
        cursor: sqlite3.Cursor = con.cursor()
    except sqlite3.Error:
        print("Can't connect to or update database.")
        sys.exit(1)
    try:
        cursor.execute(
            """CREATE TABLE articles(
                id INTEGER PRIMARY KEY,
                date VARCHAR,
                article_link VARCHAR UNIQUE,
                article_title VARCHAR,
                note VARCHAR,
                cover VARCHAR,
                cover_type VARCHAR
            )"""
        )
    except sqlite3.OperationalError:
        pass
    # Migrate existing databases that don't have the cover/cover_type columns
    for column in ("cover", "cover_type"):
        try:
            cursor.execute(f"ALTER TABLE articles ADD COLUMN {column} VARCHAR")
            con.commit()
        except sqlite3.OperationalError:
            pass
    return con


@dataclass
class Article:
    """A raindrop item destined for the articles table."""

    date: datetime
    link: str
    title: str | None
    note: str
    cover: str | None


def add_article_to_db(con, article: Article) -> bool:
    """Add article to database."""
    updated: bool = False
    try:
        with con:
            con.execute(
                "INSERT INTO articles(date, article_link, article_title, note, cover, cover_type) VALUES(?, ?, ?, ?, ?, ?)",
                (
                    article.date.isoformat(),
                    article.link,
                    article.title,
                    article.note,
                    article.cover,
                    get_image_mime_type(article.cover) if article.cover else None,
                ),
            )
        updated = True
    except sqlite3.IntegrityError:
        try:
            with con:
                res = con.execute(
                    "SELECT note, cover, cover_type FROM articles WHERE article_link=?",
                    (article.link,),
                )
                stored_note, stored_cover, stored_cover_type = res.fetchone()
                if stored_note != article.note or (article.cover and not stored_cover):
                    cover_type = stored_cover_type
                    if article.cover and not stored_cover:
                        cover_type = get_image_mime_type(article.cover)
                    con.execute(
                        "UPDATE articles SET date=?, article_title=?, note=?, cover=?, cover_type=? WHERE article_link=?",
                        (
                            article.date.isoformat(),
                            article.title,
                            article.note,
                            article.cover,
                            cover_type,
                            article.link,
                        ),
                    )
                    updated = True
        except sqlite3.IntegrityError:
            pass

    return updated


HTTP_UNAUTHORIZED = 401
HTTP_SERVER_ERROR = 500


def _print_connection_error(e: ConnectionError) -> None:
    print(
        f"Network error: Unable to connect to Raindrop API. Please check your internet connection. Error: {e}"
    )


def _print_http_error(e: HTTPError, context: str = "") -> None:
    """Print a message for an HTTPError raised while talking to the Raindrop API."""
    status = e.response.status_code if e.response is not None else None
    if status == HTTP_UNAUTHORIZED:
        print(
            "Authentication error: Invalid Raindrop API token. Please check your client_secret in the config."
        )
    elif status is not None and status >= HTTP_SERVER_ERROR:
        print(
            f"Server error: Raindrop API is currently unavailable (status {status}). Please try again later."
        )
    elif status is not None:
        print(f"HTTP error{context}: {status} - {e}")
    else:
        print(f"HTTP error{context}: {e}")


def _get_done_collection_id(arguments) -> int | None:
    """Get or create the "done" collection. Returns 0 if not needed, None on failure."""
    if not (arguments.raindrop_handled_collection and not arguments.all):
        return 0
    try:
        with API(token=arguments.client_secret) as api:
            return Collection.get_or_create(
                api=api, title=arguments.raindrop_handled_collection
            ).id
    except ConnectionError as e:
        _print_connection_error(e)
        return None
    except HTTPError as e:
        _print_http_error(e, " while setting up collection")
        return None


def _process_raindrop_item(con, api, item, arguments, done_id: int) -> bool:
    """Add a single raindrop item to the database and mark it as handled."""
    try:
        notetext: str = item.other["note"]
    except KeyError:
        notetext = ""
    url: HttpUrl | None = item.link
    # Convert HttpUrl to string for database storage
    url_str: str = str(url) if url else ""
    article = Article(
        date=item.created,
        link=url_str,
        title=item.title,
        note=notetext,
        cover=item.cover,
    )
    updated = add_article_to_db(con=con, article=article)
    # Set the tag "rss" only when processing unsorted items (not when using --all)
    if arguments.raindrop_handled_collection and not arguments.all:
        Raindrop.update(
            api=api, id=item.id, collection=done_id, link=url_str, tags=["rss"]
        )
    return updated


def check_for_new_articles(con, arguments) -> bool:
    """Check for new articles in Raindrop and add them to the database."""
    done_id = _get_done_collection_id(arguments)
    if done_id is None:
        return False

    updated = False
    try:
        with API(token=arguments.client_secret) as api:
            # Fetch all raindrops if --all flag is set, otherwise only unsorted
            if arguments.all:
                items = Raindrop.search(api=api)  # type: ignore
            else:
                items = Raindrop.search(api=api, collection=CollectionRef.Unsorted)  # type: ignore

            for item in items:
                if _process_raindrop_item(
                    con=con, api=api, item=item, arguments=arguments, done_id=done_id
                ):
                    updated = True
    except ConnectionError as e:
        _print_connection_error(e)
        return False
    except HTTPError as e:
        _print_http_error(e)
        return False
    return updated


def create_rss_feed(con, arguments):
    """Create an RSS feed from links in the database."""
    feed_description: str = arguments.feed_description

    # Create the RSS feed
    fg = FeedGenerator()
    fg.id(id=arguments.url)
    fg.author(author={"name": arguments.name, "email": arguments.email})
    fg.title(title=arguments.title)
    fg.description(description=feed_description)
    fg.link(href=arguments.url, rel="alternate")
    fg.language(language=arguments.language)

    # Add entries to the RSS feed (newest first)
    cursor = con.cursor()
    cursor.execute("""
        SELECT date, article_link, article_title, note, cover, cover_type FROM articles ORDER BY date ASC
    """)
    for date, article_link, article_title, note, cover, cover_type in cursor.fetchall():
        fe: FeedEntry = fg.add_entry()
        fe_url = article_link
        fe.link(href=fe_url)
        fe.id(fe_url)
        fe.title(article_title)
        fe.published(published=date)
        if cover:
            # Backfill cover_type for rows stored before this column existed.
            resolved_cover_type = cover_type or get_image_mime_type(cover)
            if not cover_type:
                with con:
                    con.execute(
                        "UPDATE articles SET cover_type=? WHERE article_link=?",
                        (resolved_cover_type, article_link),
                    )
            fe.enclosure(cover, 0, resolved_cover_type or DEFAULT_IMAGE_MIME_TYPE)
            summary = f'<img src="{cover}" alt="" style="max-width:100%;"/><br/>{note}'
        else:
            summary = note
        fe.summary(summary)

    return fg.atom_str(pretty=True).decode("utf-8")


def install(arguments) -> NoReturn:
    """Install css, JavaScript, svg, and favicon resources."""
    if not arguments.web_root or not arguments.web_path:
        print("No web_root or web_path in config.")
        sys.exit(1)
    if not Path(arguments.web_root + arguments.web_path).is_dir():
        Path(arguments.web_root + arguments.web_path).mkdir(parents=True, exist_ok=True)

    # Copy css, svg, JavaScript, and favicon
    files = [
        ("resources/rss.js", "rss.js"),
        ("resources/styles.css", "styles.css"),
        ("resources/rss.svg", "rss.svg"),
        ("resources/favicon.svg", "favicon.svg"),
    ]

    for src, dst_name in files:
        if not Path(src).is_file():
            print(f"No file {src}")
            sys.exit(1)
        dst = arguments.web_root + arguments.web_path + dst_name
        shutil.copy(src=src, dst=dst)

    install_path = arguments.web_root + arguments.web_path
    print(f"Installed css, svg, JavaScript, and favicon to {install_path}")
    sys.exit(0)


def set_variables(config, input_args):
    """Set arguments."""
    input_args.web_root = config.get("feed", "web_root")
    input_args.web_path = config.get("feed", "web_path")
    input_args.filename = config.get("feed", "filename")
    input_args.name = config.get("feed", "author_name")
    input_args.email = config.get("feed", "author_email")
    input_args.title = config.get("feed", "contact_title")
    input_args.url = config.get("feed", "contact_url")
    input_args.feed_description = config.get("feed", "feed_description")
    input_args.client_secret = config.get("raindrop", "client_secret")
    input_args.raindrop_handled_collection = config.get(
        "raindrop", "raindrop_handled_collection"
    )
    input_args.generate_rss = False
    input_args.db_path = config.get("feed", "db_path")
    input_args.language = config.get("feed", "language")
    return input_args


def generate_rss_feed(con, arguments) -> str:
    """Generate RSS feed with JavaScript reference for browser rendering."""
    feed_str: str = create_rss_feed(con=con, arguments=arguments)

    # Add CSS stylesheet reference
    stylesheet = (
        f"<?xml version='1.0' encoding='UTF-8'?>\n"
        f"<?xml-stylesheet href='{arguments.web_path}styles.css' type='text/css'?>"
    )
    feed_str = feed_str.replace("<?xml version='1.0' encoding='UTF-8'?>", stylesheet)

    # Add external JavaScript reference with XHTML namespace
    # Using Jake Archibald's technique:
    # https://jakearchibald.com/2025/making-xml-human-readable-without-xslt/
    # The script replaces the XML document with HTML when viewed in a browser
    script_tag = (
        f'\n  <script xmlns="http://www.w3.org/1999/xhtml" '
        f'src="{arguments.web_path}rss.js" defer="" />'
    )

    # Insert script after the opening feed tag
    # Handle both single and double quotes
    feed_str = re.sub(r"(<feed[^>]*>)", r"\1" + script_tag, feed_str, count=1)

    return feed_str


def run_raindrop2rss(args) -> Literal[True]:
    """Run raindrop2rss."""
    # Init database
    db: sqlite3.Connection = init_db(arguments=args)

    # Check for new articles
    args.generate_rss = check_for_new_articles(con=db, arguments=args)

    # Create the RSS feed string
    feed: Any = generate_rss_feed(con=db, arguments=args)

    # Print the feed if debug
    if args.stdout:
        print(feed)

    # Write the feed to a file if new articles where found
    if (
        args.generate_rss
        or not Path(args.web_root + args.web_path + args.filename).is_file()
    ):
        if not Path(args.web_root + args.web_path).is_dir():
            print("First run the command with the --install flag.")
            sys.exit(1)
        Path(args.web_root + args.web_path + args.filename).write_text(
            data=feed, encoding="utf-8"
        )

    # Close database
    db.close()

    return True


def main() -> NoReturn:
    """Main function."""
    parser = argparse.ArgumentParser(
        prog="raindrop2rss",
        description="""Tool to get links from raindrop.io and publish them as an RSS feed.""",
        epilog="""Program made by peter@reuteras.net.
            If you find a bug please let me know.""",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-o", "--stdout", action="store_true", help="Dump rss to stdout"
    )
    parser.add_argument(
        "-i",
        "--install",
        action="store_true",
        help="Install css, JavaScript, and svg resources",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Download all raindrops (not just unsorted)",
    )
    input_args: argparse.Namespace = parser.parse_args()

    # Read configuration and set variables
    configuration: configparser.RawConfigParser = read_configuration(
        config_file="raindrop2rss.cfg"
    )

    # Set configuration variables
    args: argparse.Namespace = set_variables(
        config=configuration, input_args=input_args
    )

    if args.install:
        install(arguments=args)

    run_raindrop2rss(args=args)
    sys.exit(0)


if __name__ == "__main__":
    main()
