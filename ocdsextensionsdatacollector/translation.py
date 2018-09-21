import os
import json
import gettext
from collections import OrderedDict
from docutils import nodes
from docutils.utils import new_document
from recommonmark.parser import CommonMarkParser

from ocdsdocumentationsupport.translation import translate_codelists, translate_schema # noqa


def translate_extension(domain, sourcedir, builddir, localedir, language):
    translator = gettext.translation(domain, localedir, languages=[language], fallback=language == 'en')

    os.makedirs(builddir, exist_ok=True)

    with open(os.path.join(sourcedir, 'extension.json')) as r, open(os.path.join(builddir, 'extension.json'), 'w') as w:
        data = json.load(r, object_pairs_hook=OrderedDict)
        for key in ('name', 'description'):
            if isinstance(data[key], dict):
                value = data[key]['en']
            else:
                value = data[key]
            new_value = translator.gettext(value)
            data[key] = {language: new_value}
        json.dump(data, w, indent=2, separators=(',', ': '), ensure_ascii=False)


def translate_docs(domain, source_dir, build_dir, locale_path, language, extension, version):
    parser = CommonMarkParser()
    document = new_document('{}/{}'.format(extension, version))
    visitor = TranslateMarkdown(document, domain, localedir=locale_path, language=language)
    with open(os.path.join(source_dir, 'README.md')) as f:
        english_readme = f.read()
    parser.parse(english_readme, document)
    document.walkabout(visitor)
    with open(os.path.join(build_dir, 'README.md'), 'w+') as f:
        f.write(visitor.astext())


class TranslateMarkdown(nodes.NodeVisitor):
    def __init__(self, document, domain, localedir, language):
        nodes.NodeVisitor.__init__(self, document)

        # Whether we are writing output.
        self.writing = True
        # The writing context.
        self.context = [None]
        # List item markers.
        self.markers = []
        # Table column specifications.
        self.colspecs = []
        # For zebra tables.
        self.table_row_index = 0
        # The output.
        self.text = ''

        self.translator = gettext.translation(domain, localedir, languages=[language], fallback=language == 'en')

    def append(self, text):
        if self.writing:
            self.text += text

    def translate(self, node):
        # See https://github.com/sphinx-doc/sphinx/blob/v1.5.1/sphinx/util/nodes.py#L142-L166
        message = node.rawsource.strip()
        self.append(self.translator.gettext(message))

    def astext(self):
        return self.text

    def __getattr__(self, name):
        # Otherwise, we need to implement a lot of empty methods to avoid exceptions.
        return lambda *args: None

    # Text

    def visit_Text(self, node):
        if self.context[-1] == 'block-raw':
            self.append(node.astext())

    # System

    def depart_document(self, node):
        self.text = self.text[:-1]  # remove extra newline

    def visit_system_message(self, node):
        self.writing = False

    def depart_system_message(self, node):
        self.writing = True

    # Block or inline

    def visit_raw(self, node):
        if node.parent.tagname != 'paragraph':
            self.context.append('block-raw')

    def depart_raw(self, node):
        if node.parent.tagname != 'paragraph':
            self.context.pop()
            self.append('\n\n')

    # Block

    def visit_block_quote(self, node):
        self.context.append('block-quote')

    def depart_block_quote(self, node):
        self.context.pop()

    def visit_paragraph(self, node):
        if self.context[-1] == 'block-quote':
            self.append('> ')
        self.translate(node)

    def depart_paragraph(self, node):
        if self.context[-1] not in ('th', 'td'):
            self.append('\n')
            if not self.markers:
                self.append('\n')

    def visit_literal_block(self, node):
        self.append('```{}\n'.format(node.attributes.get('language', '')))
        self.append(node.rawsource)

    def depart_literal_block(self, node):
        self.append('```\n\n')

    def visit_section(self, node):
        self.append('#' * node.attributes['level'] + ' ')

    def visit_title(self, node):
        self.translate(node)

    def depart_title(self, node):
        self.append('\n\n')

    # Lists

    def visit_bullet_list(self, node):
        self.markers.append('*')

    def visit_enumerated_list(self, node):
        self.markers.append('1.')

    def depart_bullet_list(self, node):
        self.markers.pop()
        if not self.markers:
            self.append('\n')

    def depart_enumerated_list(self, node):
        self.markers.pop()
        if not self.markers:
            self.append('\n')

    def visit_list_item(self, node):
        self.append('  ' * (len(self.markers) - 1))
        self.append('{} '.format(self.markers[-1]))

    # Some parts copied from: docutils.writers._html_base, docutils.writers.html4css1, sphinx.writers.html

    # HTML

    def html_tag(self, node, tagname=None, suffix='\n', empty=None, **attributes):
        if node:
            parts = [node.tagname]
            atts = {k: v for k, v in node.attributes.items() if v}
        else:
            parts = [tagname]
            atts = {}

        atts.update(attributes)

        if empty:
            infix = ' /'
        else:
            infix = ''

        for name, value in atts.items():
            parts.append('{}="{}"'.format(name.lower(), value))

        self.append('<{}{}>'.format(' '.join(parts), infix) + suffix)

    def close_html_tag(self, node, tagname=None, suffix='\n'):
        self.append('</{}>'.format(tagname or node.tagname) + suffix)

    def write_colspecs(self):
        if self.colspecs:
            self.html_tag(None, 'colgroup')
            width = sum(node['colwidth'] for node in self.colspecs)
            for node in self.colspecs:
                colwidth = int(node['colwidth'] * 100.0 / width + 0.5)
                self.html_tag(None, 'col', empty=True, width='{}%'.format(colwidth))
            self.colspecs = []
            self.close_html_tag(None, 'colgroup')

    # Tables

    def visit_table(self, node):
        self.table_row_index = 0
        self.html_tag(node, border='1', CLASS='docutils')

    def depart_table(self, node):
        self.close_html_tag(node, suffix='\n\n')

    def visit_colspec(self, node):
        self.colspecs.append(node)

    def visit_thead(self, node):
        self.write_colspecs()
        self.html_tag(node, valign='bottom')

    def depart_thead(self, node):
        self.close_html_tag(node)

    def visit_tbody(self, node):
        self.write_colspecs()
        self.html_tag(node, valign='top')

    def depart_tbody(self, node):
        self.close_html_tag(node)

    def visit_row(self, node):
        self.table_row_index += 1
        self.html_tag(None, 'tr', CLASS='row-odd' if self.table_row_index % 2 else 'row-even')

    def depart_row(self, node):
        self.close_html_tag(None, 'tr')

    def visit_entry(self, node):
        if isinstance(node.parent.parent, nodes.thead):
            tagname = 'th'
            atts = {'class': 'head'}
        else:
            tagname = 'td'
            atts = {}
        self.context.append(tagname)
        self.html_tag(None, tagname, suffix='', **atts)

    def depart_entry(self, node):
        self.close_html_tag(None, self.context.pop())
