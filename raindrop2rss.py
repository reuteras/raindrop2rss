#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Create rss feed for links saved to raindrop.io

import argparse
import configparser
import shutil
import sqlite3
import sys

from feedgen.feed import FeedGenerator
from html import escape
from pathlib import Path
from raindropiopy import API, Collection, CollectionRef, Raindrop

def read_configuration(config_file):
    """Read configuration file."""
    config = configparser.RawConfigParser()
    config.read(config_file)
    if not config.sections():
        print("Can't find configuration file.")
        sys.exit(1)
    return config


def init_db(arguments):
    """Init SQLite3 database for articles."""
    try:
        con = sqlite3.connect(arguments.db_path)
        cursor = con.cursor()
    except:
        sys.exit("Can't connect to or update database.")
    try:
        cursor.execute(
            "CREATE TABLE articles(id INTEGER PRIMARY KEY, date VARCHAR, article_link VARCHAR UNIQUE, article_title VARCHAR, note VARCHAR)"
        )
    except sqlite3.OperationalError:
        pass
    return con


def add_article_to_db(con, date, alink, atitle, note):
    """Add article to database."""
    updated = False
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


def check_for_new_articles(con, arguments):
    """Check for new articles in Raindrop and add them to the database."""
    updated = False
    done_id = 0

    if arguments.raindrop_handled_collection:
        with API(arguments.client_secret) as api:
            done_id = Collection.get_or_create(api, title=arguments.raindrop_handled_collection).id

    with API(arguments.client_secret) as api:
        for item in Raindrop.search(api, collection=CollectionRef.Unsorted):
            try:
                notetext = item.other['note']
            except KeyError:
                notetext = ""
            date = item.created
            title = item.title
            url = item.link
            if add_article_to_db(con, date, url, title, notetext):
                updated = True
            # Set the tag "rss" - changing collection doesn't work at the moment
            if arguments.raindrop_handled_collection:
                Raindrop.update(api, id=item.id, collection=done_id, link=url, tags=["rss"])

    return updated

def create_rss_feed(con, arguments):
    """Create an RSS feed from links in the database."""
    feed_description = arguments.feed_description

    # Create the RSS feed
    fg = FeedGenerator()
    fg.id(arguments.url)
    fg.author( {'name':arguments.name,'email':arguments.email} )
    fg.title(arguments.title)
    fg.description(feed_description)
    fg.link(href=arguments.url, rel="alternate")
    fg.language(arguments.language)

    # Add entries to the RSS feed
    cursor = con.cursor()
    cursor.execute("""
        SELECT date, article_link, article_title, note FROM articles ORDER BY id LIMIT 50
    """)
    for date, article_link, article_title, note in cursor.fetchall():
        fe = fg.add_entry()
        fe_url = article_link
        fe.link(href=fe_url)
        fe.id(fe_url)
        fe.title(escape(article_title))
        fe.published(published=date)
        fe.summary(f"{note}")

    return fg.atom_str(pretty=True).decode("utf-8")


def install(arguments):
    """Install css and xslt."""

    if not arguments.web_root or not arguments.web_path:
        sys.exit("No web_root or web_path in config.")
    if not Path(arguments.web_root + arguments.web_path).is_dir():
        Path(arguments.web_root + arguments.web_path).mkdir(parents=True, exist_ok=True)

    # Copy css and xslt
    src_xsl = "resources/rss.xsl"
    if not Path(src_xsl).is_file():
        sys.exit("No file rss.xsl")
    dst_xsl = arguments.web_root + arguments.web_path + "rss.xsl"
    shutil.copy(src_xsl, dst_xsl)
    src_css = "resources/styles.css"
    if not Path(src_css).is_file():
        sys.exit("No file styles.css")
    dst_css = arguments.web_root + arguments.web_path + "styles.css"
    shutil.copy(src_css, dst_css)

    print(f"Installed css and xslt to {arguments.web_root + arguments.web_path}")
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
    input_args.raindrop_handled_collection = config.get("raindrop", "raindrop_handled_collection")
    input_args.generate_rss = False
    input_args.db_path = config.get("feed", "db_path")
    input_args.language = config.get("feed", "language")
    return input_args


def generate_rss_feed(con, arguments):
    """Generate RSS feed."""
    feed_str = create_rss_feed(con, arguments)
    return feed_str.replace("<?xml version='1.0' encoding='UTF-8'?>","<?xml version='1.0' encoding='UTF-8'?>\n<?xml-stylesheet href='" + arguments.web_path + "rss.xsl' type='text/xsl'?>")

def run_raindrop2rss(args):
    # Init database
    db = init_db(args)

    # Check for new articles
    args.generate_rss = check_for_new_articles(db, args)

    # Create the RSS feed string
    feed = generate_rss_feed(db, args)

    # Print the feed if debug
    if args.stdout:
        print(feed)

    # Write the feed to a file if new articles where found
    if args.generate_rss or not Path(args.web_root + args.web_path + args.filename).is_file():
        if not Path(args.web_root + args.web_path).is_dir():
            sys.exit("First run the command with the --install flag.")
        Path(args.web_root + args.web_path + "rss.xml").write_text(feed)

    # Close database
    db.close()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        prog="raindrop2rss",
        description="""Tool to get links from raindrop.io and publish them as an RSS feed.""",
        epilog="""Program made by @peter.reuteras@infosec.exchange on Mastodon.
            If you find a bug please let me know.""",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-o", "--stdout", action="store_true", help="Dump rss to stdout")
    parser.add_argument("-i", "--install", action="store_true", help="Install css and xslt")
    input_args = parser.parse_args()

    # Read configuration and set variables
    configuration = read_configuration("raindrop2rss.cfg")

    # Set configuration variables
    args = set_variables(configuration, input_args)

    if args.install:
        install(args)

    run_raindrop2rss(args)

if __name__ == "__main__":
    main()
