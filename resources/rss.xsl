<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="3.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
    <xsl:output method="html" version="1.0" encoding="UTF-8" doctype-system="about:legacy-compat" indent="yes"/>
    <xsl:template match="/">
        <html lang="en">
            <head>
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1"/>
                <title>RSS feed preview | <xsl:value-of select="/atom:feed/atom:title"/></title>
                <link rel="stylesheet" href="styles.css"/>
            </head>
            <body>
                <main>
                    <header>
                        <img src="rss.svg" class="rim" style="width:100px" alt="RSS icon"/>
                        <h1>RSS feed preview</h1>
                        <p>Subscribe by copying the URL from the address bar into your newsreader.</p>
                        <p class="meta">Updated on <xsl:value-of select="translate(substring(atom:feed/atom:updated, 0, 17),'T',' ')" /></p>
                        <p><xsl:value-of select="/atom:feed/atom:subtitle"/></p>
                    </header>
                    <h2>Recent blog posts</h2>
                    <xsl:for-each select="/atom:feed/atom:entry">
                        <article>
                            <p>Published on <xsl:value-of select="translate(substring(atom:published, 0, 17),'T',' ')" /></p>
                            <p><a><xsl:attribute name="href"><xsl:value-of select="atom:link/@href"/></xsl:attribute><xsl:value-of select="atom:title"/></a></p>
                            <p><xsl:value-of select="atom:summary"/></p>
                        </article>
                    </xsl:for-each>
                </main>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
