# raindrop2rss

A tool to get links from [raindrop.io](https://raindrop.io) and create a RSS feed with the links and titles. My use case is to share links to colleagues and friends.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/reuteras/raindrop2rss.git
cd raindrop2rss
```

2. Install using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

## Configuration

1. Copy the default configuration file:
```bash
cp default-raindrop2rss.cfg raindrop2rss.cfg
```

2. Edit `raindrop2rss.cfg` with your settings:
```ini
[raindrop]
client_secret=<your Raindrop.io API token>
raindrop_handled_collection=Done

[feed]
web_path=/feeds/
web_root=/var/www/html
filename=it.xml
author_name=Your Name
author_email=your@email.com
contact_url=https://yourwebsite.com
contact_title=Your Feed Title
feed_description=Your feed description
db_path=articles.db
language=en
```

### Getting a Raindrop.io API Token

1. Go to [Raindrop.io App Settings](https://app.raindrop.io/settings/integrations)
2. Click "Create new app"
3. Once created, click on your app to get the test token
4. Copy the token to `client_secret` in your config file

## Usage

### First-time Setup

Install the required CSS, JavaScript, and SVG resources to your web directory:

```bash
uv run python raindrop2rss.py --install
```

This will copy the necessary files to the `web_root` + `web_path` location specified in your config.

### Generate the RSS Feed

Run the script to check for new articles in your Raindrop.io unsorted collection and generate the RSS feed:

```bash
uv run python raindrop2rss.py
```

The script will:
1. Connect to Raindrop.io and fetch unsorted bookmarks
2. Add new bookmarks to the local SQLite database
3. Generate an RSS feed at `web_root/web_path/filename`
4. Optionally move processed bookmarks to the collection specified in `raindrop_handled_collection`

### Command-line Options

- `-o, --stdout` - Output the RSS feed to stdout (useful for testing)
- `-i, --install` - Install CSS, JavaScript, and SVG resources
- `-v, --verbose` - Verbose output
- `-h, --help` - Show help message

### Examples

Preview the feed without writing to file:
```bash
uv run python raindrop2rss.py --stdout
```

Run as a cron job to automatically update the feed:
```bash
# Add to crontab to run every hour
0 * * * * cd /path/to/raindrop2rss && uv run python raindrop2rss.py
```

## Tips

If you need to update the SQLite3 database you can use the following command:

```bash
uvx litecli articles.db
```

## Browser-Friendly Feed Rendering

The RSS feed includes a JavaScript-based renderer that makes it human-readable when viewed in a browser, while remaining fully compatible with RSS readers. Previously this used XSLT, but browser support for XSLT is being phased out. The new JavaScript approach provides the same functionality with better long-term browser support.

When you view the feed in a browser, the JavaScript transforms the XML into a styled HTML page. RSS readers ignore this and parse the feed normally.

## Thanks to

- [raindrop.io](https://raindrop.io) - the site I use to store links to share
- I use [feedgen](https://feedgen.kiesow.be/) to create the RSS feed
- I currently use [raindrop-io-py](https://github.com/PBorocz/raindrop-io-py) to access raindrop.io
- Tips on styling the feed from [Darek Kay](https://darekkay.com/blog/rss-styling/)
