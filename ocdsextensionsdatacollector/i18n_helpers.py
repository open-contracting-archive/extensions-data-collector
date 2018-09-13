import os
from _csv import Error as CSVError

from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir, extract_from_file
from babel.messages.pofile import write_po

from ocdsextensionsdatacollector.babel_extractors import extract_codelist, extract_schema, extract_extension_meta


method_map = [
    ('**.csv', extract_codelist),
    ('**/schema/**.json', extract_schema)
]

locale_dir = 'locale'
en_dir = 'en'


def codelists_po(output_dir, extension_id, version):

    codelists_dir = os.path.join(
        output_dir, extension_id, version, 'codelists')

    if os.path.isdir(codelists_dir):
        
        po_dir = os.path.join(output_dir, locale_dir, en_dir, extension_id, version)
        if not os.path.isdir(po_dir):
            os.makedirs(po_dir, exist_ok=True)

        catalog = Catalog(project=None,
                          version=None,
                          msgid_bugs_address=None,
                          copyright_holder=None,
                          charset='utf-8')

        messages = extract_from_dir(codelists_dir, method_map)

        try:
            for filename, lineno, message, comments, context in messages:

                filepath = os.path.normpath(os.path.join(codelists_dir, filename))
                catalog.add(message, None, [(filepath, lineno)],
                            auto_comments=comments, context=context)

        except CSVError as e:
            print('Could not parse CSV for %s/%s: %s' % (extension_id, version, e))

        output_file = os.path.join(po_dir, 'codelists.po')
        with open(output_file, 'wb') as outfile:

            write_po(outfile, catalog, width=76,
                     no_location=False,
                     omit_header=False,
                     sort_output=False,
                     sort_by_file=True,
                     include_lineno=True)


def schema_po():
    # 'release-schema.json'
    pass


def extension_po():
    # 'extension.json'
    pass