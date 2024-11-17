<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
    <xsl:output method="html" version="1.0" encoding="UTF-8" doctype-system="about:legacy-compat" indent="yes"/>
    <xsl:template match="/">
        <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
            <head>
                <title>RSS feed preview | <xsl:value-of select="/atom:feed/atom:title"/></title>
                <meta charset="utf-8"/>
                <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1"/>
                <link rel="stylesheet" href="/feeds/styles.css"/>
            </head>
            <body>
                <main>
                    <header>
                        <img src="rss.svg" class="rim" style="width:200px" alt=""/>
                        <h3>This is an RSS feed</h3>
                        <p>Subscribe by copying the URL from the address bar into your newsreader.</p>
                        <div>
                            <h1>RSS feed preview</h1>
                            <p class="meta">Updated on <xsl:value-of select="translate(substring(atom:feed/atom:updated, 0, 17),'T',' ')" /></p>
                            <p><xsl:value-of select="/atom:feed/atom:subtitle"/></p>
                        </div>
                    </header>
                        
                    <h2>Recent blog posts</h2>
                    <xsl:for-each select="/atom:feed/atom:entry">
                        <div>
                            <p>Published on <xsl:value-of select="translate(substring(atom:published, 0, 17),'T',' ')" /></p>
                            <p><a><xsl:attribute name="href"><xsl:value-of select="atom:link/@href"/></xsl:attribute><xsl:value-of select="atom:title"/></a></p>
                            <p><xsl:value-of select="atom:summary"/></p>
                        </div>
                    </xsl:for-each>
                </main>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
