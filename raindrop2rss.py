#!/usr/bin/env python
"""Create rss feed for links saved to raindrop.io."""

import argparse
import configparser
import shutil
import sqlite3
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Literal, NoReturn

from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from pydantic import HttpUrl
from raindropiopy import API, Collection, CollectionRef, Raindrop
from requests.exceptions import HTTPError


def read_configuration(config_file: str) -> configparser.RawConfigParser:
    """Read configuration file."""
    config: configparser.RawConfigParser = configparser.RawConfigParser()
    config.read(filenames=config_file)
    if not config.sections():
        print("Can't find configuration file.")
        sys.exit(1)
    return config


def init_db(arguments) -> sqlite3.Connection:
    """Init SQLite3 database for articles."""
    try:
        con: sqlite3.Connection = sqlite3.connect(database=arguments.db_path)
        cursor: sqlite3.Cursor = con.cursor()
    except Exception:
        print("Can't connect to or update database.")
        sys.exit(1)
    try:
        cursor.execute(
            "CREATE TABLE articles(id INTEGER PRIMARY KEY, date VARCHAR, article_link VARCHAR UNIQUE, article_title VARCHAR, note VARCHAR)"
        )
    except sqlite3.OperationalError:
        pass
    return con


def add_article_to_db(con, date, alink, atitle, note: str) -> bool:
    """Add article to database."""
    updated: bool = False
    try:
        with con:
            con.execute(
                "INSERT INTO articles(date, article_link, article_title, note) VALUES(?, ?, ?, ?)",
                (date.isoformat(), alink, atitle, note),
            )
        updated = True
    except sqlite3.IntegrityError:
        try:
            with con:
                res = con.execute(
                    "SELECT note FROM articles WHERE article_link=?", (alink,)
                )
                if not res.fetchone()[0] == note:
                    con.execute(
                        "UPDATE articles SET date=?, article_title=?, note=? WHERE article_link=?",
                        (date.isoformat(), atitle, note, alink),
                    )
                    updated = True
        except sqlite3.IntegrityError:
            pass

    return updated


def check_for_new_articles(con, arguments) -> bool:
    """Check for new articles in Raindrop and add them to the database."""
    updated = False
    done_id: int = 0

    # Only set up "done" collection if not downloading all items
    if arguments.raindrop_handled_collection and not arguments.all:
        try:
            with API(token=arguments.client_secret) as api:
                done_id = Collection.get_or_create(
                    api=api, title=arguments.raindrop_handled_collection
                ).id
        except (HTTPError, ConnectionError):
            pass

    try:
        with API(token=arguments.client_secret) as api:
            # Fetch all raindrops if --all flag is set, otherwise only unsorted
            if arguments.all:
                items = Raindrop.search(api=api)  # type: ignore
            else:
                items = Raindrop.search(api=api, collection=CollectionRef.Unsorted)  # type: ignore

            for item in items:
                try:
                    notetext: str = item.other["note"]
                except KeyError:
                    notetext: str = ""
                date: datetime | None = item.created
                title: str | None = item.title
                url: HttpUrl | None = item.link
                if add_article_to_db(
                    con=con, date=date, alink=url, atitle=title, note=notetext
                ):
                    updated = True
                # Set the tag "rss" only when processing unsorted items (not when using --all)
                if arguments.raindrop_handled_collection and not arguments.all:
                    Raindrop.update(
                        api=api, id=item.id, collection=done_id, link=url, tags=["rss"]
                    )
    except (HTTPError, ConnectionError):
        pass
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
        SELECT date, article_link, article_title, note FROM articles ORDER BY id DESC
    """)
    for date, article_link, article_title, note in cursor.fetchall():
        fe: FeedEntry = fg.add_entry()
        fe_url = article_link
        fe.link(href=fe_url)
        fe.id(fe_url)
        fe.title(escape(article_title))
        fe.published(published=date)
        fe.summary(f"{note}")

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

    print(f"Installed css, svg, JavaScript, and favicon to {arguments.web_root + arguments.web_path}")
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
    feed_str = feed_str.replace(
        "<?xml version='1.0' encoding='UTF-8'?>",
        f"<?xml version='1.0' encoding='UTF-8'?>\n<?xml-stylesheet href='{arguments.web_path}styles.css' type='text/css'?>"
    )

    # Add external JavaScript reference with XHTML namespace
    # Using Jake Archibald's technique: https://jakearchibald.com/2025/making-xml-human-readable-without-xslt/
    # The script replaces the XML document with HTML when viewed in a browser
    script_tag = f'\n  <script xmlns="http://www.w3.org/1999/xhtml" src="{arguments.web_path}rss.js" defer="" />'

    # Insert script after the opening feed tag - handle both single and double quotes
    import re
    feed_str = re.sub(
        r'(<feed[^>]*>)',
        r'\1' + script_tag,
        feed_str,
        count=1
    )

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
        epilog="""Program made by @peter.reuteras@infosec.exchange on Mastodon.
            If you find a bug please let me know.""",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-o", "--stdout", action="store_true", help="Dump rss to stdout"
    )
    parser.add_argument(
        "-i", "--install", action="store_true", help="Install css, JavaScript, and svg resources"
    )
    parser.add_argument(
        "-a", "--all", action="store_true", help="Download all raindrops (not just unsorted)"
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
