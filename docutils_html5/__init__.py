#! -*- coding: utf-8 -*-
# $Id: __init__.py 6153 2009-10-05 13:37:10Z milde $
# Author: James H. Fisher <jameshfisher@gmail.com>
# Copyright: This module has been placed in the public domain.

"""
Simple document tree Writer for HTML5.

The output contains a minimum of formatting information.

The cascading style sheet "html5css3.css" is required
for proper viewing with a modern graphical browser.
"""

__docformat__ = 'reStructuredText'

"""
CSS for this module is based on the following principles:

- don't override default browser representation of semantic elements
  (e.g. <cite>)
- don't use non-semantic classes (e.g. "list-style: lower-alpha" should be
  directly in the HTML 'style' attribute)
- Don't identify presentational aspects where CSS can; e.g. class="first"
  should instead use the :first-child pseudo-selector
- minimal in space (crush it if embedding)

"""

helper_css = u"""
body { font-family: Gentium Basic; width: 40em; margin: 0 auto 0 auto; }
.docutils dt { font-weight: bold; }
.docutils dd { margin-bottom: 1em; }
.docutils header th { text-align: left; padding-right: 1em;}
.docutils header th:after { content: ":"; }
.docutils hgroup *:first-child { margin-bottom: 0;}
.docutils hgroup *:nth-child(2) { margin-top: 0; }
.docutils table.option-list th {
    font-weight: normal;
    vertical-align: top;
    text-align: left;
}
.docutils table.option-list th span { margin: 0; padding: 0; }
.docutils a.ref { vertical-align: super; }
.docutils div.footnote { display: table; }
.docutils div.footnote * { display: table-cell; }
.docutils div.footnote a { min-width: 3em; }
"""

from lxml.html import tostring, etree, fromstring
from copy import deepcopy

try:
    from dateutil.parser import parse as dateutil_date_string_parse
except ImportError:
    def date_string_parse(s):
        raise ValueError("dateutil library not found")
else:
    def date_string_parse(s):
        return dateutil_date_string_parse(s).isoformat()

"""
Docutils imports
````````````````
"""

import docutils
from docutils import nodes, writers

text_content = etree.XPath("string()")


class Writer(writers.Writer):

    supported = ('html', 'html5', 'html5css3')  # Formats this writer supports

    visitor_attributes = ('title', 'html_title')

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = HTML5Translator

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        for attr in self.visitor_attributes:
            setattr(self, attr, getattr(visitor, attr))
        #Pop the header
        self.fragment = deepcopy(visitor.article)
        self.fragment.remove(self.fragment[0])
        self.fragment = tostring(self.fragment)
        self.output = visitor.astext()

    def assemble_parts(self):
        writers.Writer.assemble_parts(self)
        for part in self.visitor_attributes:
            self.parts[part] = getattr(self, part)
        self.parts['fragment'] = self.fragment


def add_text(node, text):
    if len(node):
        if node[-1].tail == None:
            node[-1].tail = ""
        node[-1].tail += text
    else:
        if node.text == None:
            node.text = ""
        node.text += text


class HTML5Translator(nodes.NodeVisitor):

    doctype = "<!doctype html>"

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        self.settings = document.settings
        self.top_level_id = getattr(document.settings, 'top_level_id', None)
        self.top_level_class = getattr(document.settings, 'top_level_class',
                None)
        if hasattr(self.settings, 'initial_header_level'):
            self.level = self.settings.initial_header_level - 1
        self.html_title = ''
        self.title = ''
        self.title_node = None
        self.in_document_title = False
        self.settings.cloak_email_addresses = getattr(self.settings,
            'cloak_email_addresses', False)

    def astext(self):
        compact(self.html)
        return self.doctype + "\n" + tostring(self.html,
                pretty_print=True)

    def cloak_mailto(self, uri):
        """Try to hide a mailto: URL from harvesters."""
        # Encode "@" using a URL octet reference (see RFC 1738).
        # Further cloaking with HTML entities will be done in the
        # `attval` function.
        return uri.replace('@', '%40')

    def cloak_email(self, addr):
        """Try to hide the link text of a email link from harvesters."""
        # Surround at-signs and periods with <span> tags.  ("@" has
        # already been encoded to "&#64;" by the `encode` method.)
        addr = addr.replace('&#64;', '<span>&#64;</span>')
        addr = addr.replace('.', '<span>&#46;</span>')
        return addr

    def cur_el(self):
        return self.el[-1]

    def set_cur_el(self, val):
        self.el[-1] = val

    def visit_Text(self, node):
        add_text(self.cur_el(), node.astext())

    def depart_Text(self, node):
        pass

    def visit_comment(self, node):
        """Simply omit comments."""
        pass

    def depart_comment(self, node):
        pass

    def visit_reference(self, node):
        atts = {'class': 'reference'}
        if 'refuri' in node:
            atts['href'] = node['refuri']
            if (self.settings.cloak_email_addresses
                 and atts['href'].startswith('mailto:')):
                atts['href'] = self.cloak_mailto(atts['href'])
                self.in_mailto = 1
            atts['class'] += ' external'
        else:
            assert 'refid' in node, \
                   'References must have "refuri" or "refid" attribute.'
            atts['href'] = '#' + node['refid']
            atts['class'] += ' internal'
        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)
            atts['class'] += ' image-reference'
        self.set_cur_el(etree.SubElement(self.cur_el(), 'a', **atts))

    def visit_document(self, node):
        self.html = etree.Element("html")
        self.head = etree.SubElement(self.html, "head")
        # The body element everything is to be added to
        self.body = etree.SubElement(self.html, "body")
        attrs = {}
        if self.top_level_id:
            attrs['id'] = self.top_level_id
        if self.top_level_class:
            attrs['class'] = self.top_level_class
        self.article = etree.SubElement(self.body, "article", **attrs)
        # Namespacing everything for the CSS
        self.section = self.article
        # Meta-information goes here
        #self.header = etree.SubElement(self.article, "header")
        # The current element
        self.el = [self.article]
        self.add_meta("generator",
            "Docutils %s: http://docutils.sourceforge.net/" %
            docutils.__version__)
        etree.SubElement(self.head, "style", type="text/css").text = helper_css

    def depart_document(self, node):
        pass

    def visit_target(self, node):
        pass

    def depart_target(self, node):
        # Do nothing,
        pass

    def encode(self, text):
        """Encode special characters in `text` & return."""
        # @@@ A codec to do these and all other HTML entities would be nice.
        text = unicode(text)
        return text.translate({
            ord('&'): u'&amp;',
            ord('<'): u'&lt;',
            ord('"'): u'&quot;',
            ord('>'): u'&gt;',
            # may thwart some address harvesters
            ord('@'): u'&#64;',
            # TODO: convert non-breaking space only if needed?
            0xa0: u'&nbsp;'})  # non-breaking space

    def visit(self, name, node, **attrs):
        if 'id' not in attrs:
            if node.get('ids', []):
                attrs['id'] = node.get('ids')[0]
        classes = node.get('classes', [])
        previous_class = attrs.get('class', '')
        previous_class += ' '.join(classes)
        if previous_class:
            attrs['class'] = previous_class
        self.set_cur_el(etree.SubElement(self.cur_el(), name, **attrs))
        return self.cur_el()

    def depart(self):
        self.set_cur_el(self.cur_el().getparent())

    def add(self, name, **attrs):
        return etree.SubElement(self.cur_el(), name, **attrs)

    def local_header(self):
        # Get the appropriate header for attaching titles or docinfo
        tmp = self.cur_el()
        while True:
            if tmp.tag in ("section", "article"):
                headers = tmp.xpath('header')
                if len(headers) > 0:
                    header = headers[0]
                else:
                    header = etree.SubElement(tmp, "header")
                return header
            else:
                # Go up one
                parent = tmp.parent()
                if parent == tmp:
                    # Shouldn't happen
                    return None
                else:
                    tmp = parent

    def add_meta(self, attr, val):
        etree.SubElement(self.html.xpath("/html/head")[0], "meta",
                attrib={'name': attr, 'content': val})

    def visit_title(self, node):
        self.level += 1
        title = etree.SubElement(self.local_header(), "h" + str(self.level))
        if self.section.tag == 'article':
            self.in_document_title = True
            self.title_node = title
        self.el.append(title)

    def depart_title(self, node):
        if self.in_document_title:
            self.in_document_title = False
            self.html_title = tostring(self.title_node)
            self.title = text_content(self.title_node)
        self.el.pop()

    def visit_subtitle(self, node):
        self.wrap_in_section(node)
        self.el.append(etree.SubElement(self.local_header(),
            "h" + str(self.level + 1)))

    def depart_subtitle(self, node):
        self.el.pop()

    def visit_section(self, node):
        self.section = self.visit("section", node)

    def depart_section(self, node):
        self.level -= 1
        self.depart()

    def visit_docinfo(self, node):
        self.local_header().set("itemscope", "true")

    def depart_docinfo(self, node):
        pass

    def local_docinfo(self):
        local_header = self.local_header()
        tbodies = local_header.xpath("table/tbody")
        if len(tbodies) > 0:
            return tbodies[0]
        return etree.SubElement(etree.SubElement(local_header, "table"),
                "tbody")

    def prep_docinfo(self, human, machine):
        tr = etree.SubElement(self.local_docinfo(), "tr")
        etree.SubElement(tr, "th").text = human
        return etree.SubElement(tr, "td", itemprop=machine)

    def visit_author(self, node):
        self.el.append(self.prep_docinfo("Author", "author"))

    def depart_author(self, node):
        el = self.el.pop()
        self.add_meta("author", el.text)

    def visit_date(self, node):
        self.el.append(self.prep_docinfo("Date", "date"))
        self.visit("time", node)
        try:
            iso_date = date_string_parse(node.children[0].astext())
        except ValueError:
            pass
        else:
            self.cur_el().set("datetime", iso_date)

    def depart_date(self, node):
        time = self.el.pop()
        self.add_meta("date", time.get("datetime", time.text))

    def visit_colspec(self, node):
        pass

    def depart_colspec(self, node):
        pass

    def visit_thead(self, node):
        self.visit("thead", node)
        self.in_thead = True

    def depart_thead(self, node):
        self.depart()
        self.in_thead = False

    def visit_entry(self, node):
        try:
            if self.in_thead:
                el = self.visit("th", node)
            else:
                el = self.visit("td", node)
        except AttributeError:
            el = self.visit("td", node)
        rowspan = node.attributes.get('morerows', 0) + 1
        colspan = node.attributes.get('morecols', 0) + 1
        if rowspan > 1:
            el.set("rowspan", str(rowspan))
        if colspan > 1:
            el.set("colspan", str(colspan))

    def depart_entry(self, node):
        self.depart()

    def visit_image(self, node):
        self.visit("img", node)
        self.cur_el().set("src", node.attributes['uri'])

    def depart_image(self, node):
        self.depart()

    def visit_definition_list_item(self, node):
        pass

    def depart_definition_list_item(self, node):
        pass

    def visit_enumerated_list(self, node):
        el = self.visit("ol", node)
        html_list_style = {
            # Default. Don't bother specifying it; it just makes ugly HTML.
            'arabic': None,
            'loweralpha': 'lower-alpha',
            'upperalpha': 'upper-alpha',
            'lowerroman': 'lower-roman',
            'upperroman': 'upper-roman',
            }[node.attributes['enumtype']]
        if html_list_style:
            el.set("style", "list-style: %s;" % html_list_style)

    def depart_enumerated_list(self, node):
        self.depart()

    def visit_option_argument(self, node):
        el = self.visit("span", node)
        el.set("class", "option-delimiter")
        el.text = node.attributes['delimiter']
        self.depart()
        el = self.visit("var", node)

    def depart_option_argument(self, node):
        self.depart()

    def visit_option_group(self, node):
        self.visit("th", node)
        self.visit("kbd", node)

    def depart_option_group(self, node):
        self.depart()
        self.depart()

    def visit_line_block(self, node):
        try:
            self.line_block_indent
        except AttributeError:
            self.line_block_indent = -1
        self.line_block_indent += 1

    def depart_line_block(self, node):
        self.line_block_indent -= 1

    def visit_line(self, node):
        el = self.cur_el()
        add_text(el, u" " * (self.line_block_indent * 4))

    def depart_line(self, node):
        self.add("br")

    def visit_footnote_reference(self, node):
        self.visit("a", node, href="#" + node.attributes['refid'],
                id=node.attributes['ids'][0], **{"class": "ref"})

    def depart_footnote_reference(self, node):
        self.depart()

    def visit_footnote(self, node):
        self.visit("div", node, **{"class": "footnote"})

    def depart_footnote(self, node):
        self.depart()

    def visit_label(self, node):
        self.visit("a", node, id=node.parent.attributes['ids'][0],
                href="#" + node.parent.attributes['backrefs'][0])

    def depart_label(self, node):
        self.depart()

    def wrap_in_section(self, node):
        """Wrap top level paragraphs in a section element."""
        if (isinstance(node.parent, nodes.document) and
            self.section.tag == 'article'):
            self.section = self.visit('section', node, id='id1')

    def visit_paragraph(self, node):
        self.wrap_in_section(node)
        self.visit('p', node)

    def visit_tgroup(self, node):
        pass

    def depart_tgroup(self, node):
        pass

    def unknown_visit(self, node):
        simple_element = self.simple_elements[node.__class__.__name__]
        cur_el = self.visit(simple_element.html_tag_name, node)
        if simple_element.classes:
            cur_el.set("class", simple_element.classes)
        for k in simple_element.attribute_map.keys():
            attr = node.attributes.get(k, None)
            if attr:
                cur_el.set(simple_element.attribute_map[k], attr)

    def unknown_departure(self, node):
        self.depart()

    def visit_title_reference(self, node):
        self.visit('cite', node)

    def depart_title_reference(self, node):
        self.depart()

    def visit_raw(self, node):
        if 'html' in node.get('format', '').split():
            self.cur_el().append(fromstring(node.astext()))
        # Keep non-HTML raw text out of output:
        raise nodes.SkipNode

    def depart_raw(self, node):
        self.depart()

    def visit_system_message(self, node):
        self.visit('samp', node)
        self.visit('pre', node)

    def depart_system_message(self, node):
        self.depart()
        self.depart()


class Tag:
    def __init__(self, html_tag_name, classes=None, attribute_map={}):
        self.html_tag_name = html_tag_name
        self.classes = classes
        self.attribute_map = attribute_map

simple_elements = {         # HTML equiv.
    "abbreviation": Tag("abbr"),
    "acronym": Tag("acronym"),
    "attribution": Tag("cite"),
    "block_quote": Tag("blockquote"),
    "bullet_list": Tag("ul"),
    "caption": Tag("figcaption"),
    "definition": Tag("dd"),
    "definition_list": Tag("dl"),
    "description": Tag("td"),
    "emphasis": Tag("em"),
    "field": Tag("tr", "field"),
    "field_body": Tag("td", "field-body"),
    "field_name": Tag("td", "field-name"),
    "figure": Tag("figure"),
    "image": Tag("img", attribute_map={"uri": "src", "alt": "alt"}),
    "list_item": Tag("li"),
    "literal": Tag("samp"),
    "literal_block": Tag("pre"),
    "option": Tag("span"),
    "option_list": Tag("table", "option-list"),
    "option_list_item": Tag("tr"),
    "option_string": Tag("span", "option"),
    "row": Tag("tr"),
    "strong": Tag("strong"),
    "subscript": Tag("sub"),
    "superscript": Tag("sup"),
    "table": Tag("table"),
    "tbody": Tag("tbody"),
    "term": Tag("dt"),
    "transition": Tag("hr")
    }

HTML5Translator.simple_elements = simple_elements

classy_elements = ["topic"]


def visit_rst_name_classy(self, node):
    # Can't use 'class' directly; it's a keyword
    self.visit("div",
            **{'class': self.classy_elements[node.__class__.__name__]})

for rst_name in classy_elements:
    setattr(HTML5Translator, "visit_" + rst_name, visit_rst_name_classy)


def compact(html_tree):
    """
    Given an HTML tree, compact it.  This involves:

    - finding all nodes with a single non-text child node
    - checking the pair (parent, child) in following lists,
        and it is in the list, replace the pair with the appropriate
        element of the two:

        Replace with parent:
        *, p

        Replace with child:
        hgroup, h*
    """
    for p in html_tree.xpath("//p"):
        parent = p.getparent()
        if len(parent) == 1 and parent.text == None:
            parent.text = p.text
            for c in p:
                parent.append(c)
        parent.remove(p)
