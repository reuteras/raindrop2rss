# raindrop2rss

A tool to get links from [raindrop.io](https://raindrop.io) and create a RSS feed with the links and titles. My use case is to share links to colleagues and friends.

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
