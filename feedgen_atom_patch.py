"""Patch for a feedgen==1.0.0 bug that drops attributes from Atom <link> elements.

feedgen.entry.FeedEntry.atom_entry() shadows its own loop variable
(`for link in self.__atom_link: link = xml_elem(...)`), so `link.get('rel')`
ends up calling lxml.etree._Element.get() on the freshly created element
instead of reading the original link dict. rel/type/hreflang/title/length
are silently dropped from every Atom link, including the rel="enclosure"
link that FeedEntry.enclosure() relies on. Fixed upstream would remove the
shadowing; until a fixed release exists, this monkeypatches the method with
a corrected copy. Remove this module if feedgen ships a fix.
"""

from feedgen.entry import FeedEntry, _add_text_elm
from feedgen.util import xml_elem


def _patched_atom_entry(self, extensions=True):
    entry = xml_elem("entry")
    if not (
        self._FeedEntry__atom_id
        and self._FeedEntry__atom_title
        and self._FeedEntry__atom_updated
    ):
        raise ValueError("Required fields not set")
    id_elem = xml_elem("id", entry)
    id_elem.text = self._FeedEntry__atom_id
    title = xml_elem("title", entry)
    title.text = self._FeedEntry__atom_title
    updated = xml_elem("updated", entry)
    updated.text = self._FeedEntry__atom_updated.isoformat()

    if not self._FeedEntry__atom_content:
        links = self._FeedEntry__atom_link or []
        if not [link for link in links if link.get("rel") == "alternate"]:
            raise ValueError(
                "Entry must contain an alternate link or a content element."
            )

    for a in self._FeedEntry__atom_author or []:
        if not a.get("name"):
            continue
        author = xml_elem("author", entry)
        name = xml_elem("name", author)
        name.text = a.get("name")
        if a.get("email"):
            email = xml_elem("email", author)
            email.text = a.get("email")
        if a.get("uri"):
            uri = xml_elem("uri", author)
            uri.text = a.get("uri")

    _add_text_elm(entry, self._FeedEntry__atom_content, "content")

    for link_data in self._FeedEntry__atom_link or []:
        link_elem = xml_elem("link", entry, href=link_data["href"])
        if link_data.get("rel"):
            link_elem.attrib["rel"] = link_data["rel"]
        if link_data.get("type"):
            link_elem.attrib["type"] = link_data["type"]
        if link_data.get("hreflang"):
            link_elem.attrib["hreflang"] = link_data["hreflang"]
        if link_data.get("title"):
            link_elem.attrib["title"] = link_data["title"]
        if link_data.get("length"):
            link_elem.attrib["length"] = link_data["length"]

    _add_text_elm(entry, self._FeedEntry__atom_summary, "summary")

    for c in self._FeedEntry__atom_category or []:
        cat = xml_elem("category", entry, term=c["term"])
        if c.get("scheme"):
            cat.attrib["scheme"] = c["scheme"]
        if c.get("label"):
            cat.attrib["label"] = c["label"]

    for c in self._FeedEntry__atom_contributor or []:
        if not c.get("name"):
            continue
        contrib = xml_elem("contributor", entry)
        name = xml_elem("name", contrib)
        name.text = c.get("name")
        if c.get("email"):
            email = xml_elem("email", contrib)
            email.text = c.get("email")
        if c.get("uri"):
            uri = xml_elem("uri", contrib)
            uri.text = c.get("uri")

    if self._FeedEntry__atom_published:
        published = xml_elem("published", entry)
        published.text = self._FeedEntry__atom_published.isoformat()

    if self._FeedEntry__atom_rights:
        rights = xml_elem("rights", entry)
        rights.text = self._FeedEntry__atom_rights

    if self._FeedEntry__atom_source:
        source = xml_elem("source", entry)
        if self._FeedEntry__atom_source.get("title"):
            source_title = xml_elem("title", source)
            source_title.text = self._FeedEntry__atom_source["title"]
        if self._FeedEntry__atom_source.get("link"):
            xml_elem("link", source, href=self._FeedEntry__atom_source["link"])

    if extensions:
        for ext in self._FeedEntry__extensions.values() or []:
            if ext.get("atom"):
                ext["inst"].extend_atom(entry)

    return entry


def apply() -> None:
    """Replace the buggy FeedEntry.atom_entry with the corrected version."""
    FeedEntry.atom_entry = _patched_atom_entry
