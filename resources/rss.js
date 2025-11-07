/**
 * RSS/Atom Feed Browser Renderer
 * Transforms Atom feed XML into human-readable HTML for browser viewing
 * while maintaining compatibility with RSS readers.
 *
 * Based on Jake Archibald's approach: https://jakearchibald.com/2025/making-xml-human-readable-without-xslt/
 */

(function () {
  'use strict'

  // Wait for the entire document to be loaded before transforming
  // In XML documents, defer doesn't work like HTML, so we need to wait
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', transformFeed)
  } else {
    transformFeed()
  }

  function transformFeed () {
    const atomNS = 'http://www.w3.org/2005/Atom'
    const xhtmlNS = 'http://www.w3.org/1999/xhtml'

    // Get the original XML feed element
    const feed = document.documentElement

    /**
     * Get text content from XML element, handling namespace
     */
    function getElementText (parent, tagName, namespace) {
      const elements = parent.getElementsByTagNameNS(namespace, tagName)
      return elements.length > 0 ? elements[0].textContent.trim() : ''
    }

    /**
     * Get attribute value from XML element
     */
    function getElementAttribute (parent, tagName, namespace, attrName) {
      const elements = parent.getElementsByTagNameNS(namespace, tagName)
      return elements.length > 0 ? elements[0].getAttribute(attrName) || '' : ''
    }

    /**
     * Format ISO datetime string to human-readable format
     */
    function formatDate (isoString) {
      if (!isoString) return ''
      return isoString.substring(0, 16).replace('T', ' ')
    }

    /**
     * Create an HTML element with proper namespace
     */
    function html (tagName) {
      return document.createElementNS(xhtmlNS, tagName)
    }

    /**
     * Escape HTML special characters
     */
    function escapeHtml (text) {
      const div = html('div')
      div.textContent = text
      return div.innerHTML
    }

    // Extract feed metadata
    const feedTitle = getElementText(feed, 'title', atomNS)
    const feedSubtitle = getElementText(feed, 'subtitle', atomNS)
    const feedUpdated = getElementText(feed, 'updated', atomNS)

    // Get base path from current location for assets
    const currentPath = window.location.pathname
    const basePath = currentPath.substring(0, currentPath.lastIndexOf('/') + 1)

    // Create HTML structure
    const htmlRoot = html('html')
    htmlRoot.setAttribute('lang', 'en')

    // Head
    const head = html('head')

    const metaCharset = html('meta')
    metaCharset.setAttribute('charset', 'utf-8')
    head.appendChild(metaCharset)

    const metaViewport = html('meta')
    metaViewport.setAttribute('name', 'viewport')
    metaViewport.setAttribute('content', 'width=device-width, initial-scale=1')
    head.appendChild(metaViewport)

    const title = html('title')
    title.textContent = `RSS feed preview | ${feedTitle}`
    head.appendChild(title)

    const linkCSS = html('link')
    linkCSS.setAttribute('rel', 'stylesheet')
    linkCSS.setAttribute('href', basePath + 'styles.css')
    head.appendChild(linkCSS)

    const linkFavicon = html('link')
    linkFavicon.setAttribute('rel', 'icon')
    linkFavicon.setAttribute('type', 'image/svg+xml')
    linkFavicon.setAttribute('href', basePath + 'favicon.svg')
    head.appendChild(linkFavicon)

    htmlRoot.appendChild(head)

    // Body
    const body = html('body')
    const main = html('main')

    // Header
    const header = html('header')

    const img = html('img')
    img.setAttribute('src', basePath + 'rss.svg')
    img.setAttribute('class', 'rim')
    img.setAttribute('style', 'width:100px')
    img.setAttribute('alt', 'RSS icon')
    header.appendChild(img)

    const h1 = html('h1')
    h1.textContent = 'RSS feed preview'
    header.appendChild(h1)

    const metaPara = html('p')
    metaPara.setAttribute('class', 'meta')
    metaPara.textContent = `Updated on ${formatDate(feedUpdated)}`
    header.appendChild(metaPara)

    const subtitlePara = html('p')
    subtitlePara.textContent = feedSubtitle
    header.appendChild(subtitlePara)

    const instructionsPara = html('p')
    instructionsPara.textContent = 'Subscribe by copying the URL from the address bar into your newsreader.'
    header.appendChild(instructionsPara)

    main.appendChild(header)

    // Entries
    const h2 = html('h2')
    h2.textContent = 'Recent blog posts'
    main.appendChild(h2)

    const entries = feed.getElementsByTagNameNS(atomNS, 'entry')
    for (let i = 0; i < entries.length; i++) {
      const entry = entries[i]
      const entryTitle = getElementText(entry, 'title', atomNS)
      const entryLink = getElementAttribute(entry, 'link', atomNS, 'href')
      const published = getElementText(entry, 'published', atomNS)
      const summary = getElementText(entry, 'summary', atomNS)

      const article = html('article')

      const h3 = html('h3')
      const a = html('a')
      a.setAttribute('href', entryLink)
      a.textContent = entryTitle
      h3.appendChild(a)
      article.appendChild(h3)

      const datePara = html('p')
      datePara.setAttribute('class', 'meta')
      datePara.textContent = `Published on ${formatDate(published)}`
      article.appendChild(datePara)

      if (summary) {
        const summaryPara = html('p')
        summaryPara.textContent = summary
        article.appendChild(summaryPara)
      }

      main.appendChild(article)
    }

    body.appendChild(main)
    htmlRoot.appendChild(body)

    // Replace the XML root with the HTML root
    // Note: This may trigger harmless errors in Vivaldi's internal animation detection code
    // The feed will still display correctly
    document.replaceChild(htmlRoot, document.documentElement)
  }
})()
