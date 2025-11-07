/**
 * RSS/Atom Feed Browser Renderer
 * Transforms Atom feed XML into human-readable HTML for browser viewing
 * while maintaining compatibility with RSS readers.
 */

(function() {
    'use strict';

    // Only run in browser context, not in RSS readers
    if (typeof window === 'undefined' || typeof document === 'undefined') {
        return;
    }

    // Check if we're viewing XML (not already transformed)
    if (document.contentType !== 'application/xml' &&
        document.contentType !== 'text/xml' &&
        !document.contentType.includes('xml')) {
        return;
    }

    /**
     * Get text content from XML element, handling namespace
     * @param {Element} parent - Parent XML element
     * @param {string} tagName - Tag name to find
     * @param {string} namespace - XML namespace URI
     * @returns {string} Text content or empty string
     */
    function getElementText(parent, tagName, namespace) {
        const elements = parent.getElementsByTagNameNS(namespace, tagName);
        return elements.length > 0 ? elements[0].textContent : '';
    }

    /**
     * Get attribute value from XML element
     * @param {Element} parent - Parent XML element
     * @param {string} tagName - Tag name to find
     * @param {string} namespace - XML namespace URI
     * @param {string} attrName - Attribute name
     * @returns {string} Attribute value or empty string
     */
    function getElementAttribute(parent, tagName, namespace, attrName) {
        const elements = parent.getElementsByTagNameNS(namespace, tagName);
        return elements.length > 0 ? elements[0].getAttribute(attrName) || '' : '';
    }

    /**
     * Format ISO datetime string to human-readable format
     * @param {string} isoString - ISO 8601 datetime string
     * @returns {string} Formatted date string
     */
    function formatDate(isoString) {
        if (!isoString) return '';
        // Extract date and time, replace T with space, and limit to 16 chars (YYYY-MM-DD HH:MM)
        return isoString.substring(0, 16).replace('T', ' ');
    }

    /**
     * Transform Atom feed XML to HTML
     */
    function transformFeed() {
        const atomNS = 'http://www.w3.org/2005/Atom';
        const feed = document.documentElement;

        // Extract feed metadata
        const feedTitle = getElementText(feed, 'title', atomNS);
        const feedSubtitle = getElementText(feed, 'subtitle', atomNS);
        const feedUpdated = getElementText(feed, 'updated', atomNS);

        // Get base path from current location for assets
        const currentPath = window.location.pathname;
        const basePath = currentPath.substring(0, currentPath.lastIndexOf('/') + 1);

        // Build HTML structure
        const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RSS feed preview | ${escapeHtml(feedTitle)}</title>
    <link rel="stylesheet" href="${basePath}styles.css">
</head>
<body>
    <main>
        <header>
            <img src="${basePath}rss.svg" class="rim" style="width:100px" alt="RSS icon">
            <h1>RSS feed preview</h1>
            <p class="meta">Updated on ${escapeHtml(formatDate(feedUpdated))}</p>
            <p>${escapeHtml(feedSubtitle)}</p>
            <p>Subscribe by copying the URL from the address bar into your newsreader.</p>
        </header>
        <h2>Recent blog posts</h2>
        ${generateEntries(feed, atomNS)}
    </main>
</body>
</html>`;

        // Replace document content
        document.open();
        document.write(html);
        document.close();
    }

    /**
     * Generate HTML for feed entries
     * @param {Element} feed - Feed XML element
     * @param {string} atomNS - Atom namespace URI
     * @returns {string} HTML string for all entries
     */
    function generateEntries(feed, atomNS) {
        const entries = feed.getElementsByTagNameNS(atomNS, 'entry');
        let html = '';

        for (let i = 0; i < entries.length; i++) {
            const entry = entries[i];
            const title = getElementText(entry, 'title', atomNS);
            const link = getElementAttribute(entry, 'link', atomNS, 'href');
            const published = getElementText(entry, 'published', atomNS);
            const summary = getElementText(entry, 'summary', atomNS);

            html += `
        <article>
            <h3><a href="${escapeHtml(link)}">${escapeHtml(title)}</a></h3>
            <p class="meta">Published on ${escapeHtml(formatDate(published))}</p>
            <p>${escapeHtml(summary)}</p>
        </article>`;
        }

        return html;
    }

    /**
     * Escape HTML special characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Run transformation when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', transformFeed);
    } else {
        transformFeed();
    }
})();
