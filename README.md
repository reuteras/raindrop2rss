# raindrop2rss

A tool to get links from [raindrop.io](https://raindrop.io) and create a RSS feed with the links and titles. My use case is to share links to colleagues and friends.

## Tips

If you need to update the SQLite3 database you can use the following command:

```bash
uvx litecli articles.db
```

## Thanks to

- [raindrop.io](https://raindrop.io) - the site I use to store links to share
- I use [feedgen](https://feedgen.kiesow.be/) to create the RSS feed
- I currently use [raindrop-io-py](https://github.com/PBorocz/raindrop-io-py) to access raindrop.io
- Tips on styling the feed from [Darek Kay](https://darekkay.com/blog/rss-styling/)

