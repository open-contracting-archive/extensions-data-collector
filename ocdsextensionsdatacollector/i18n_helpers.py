import os
from decouple import config, UndefinedValueError
from _csv import Error as CSVError
import shutil
import glob
from contextlib import redirect_stdout, redirect_stderr
import io

import sphinx
from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir, extract_from_file
from babel.messages.pofile import write_po
from transifex.api import TransifexAPI
from transifex.util import slugify
from transifex.exceptions import TransifexAPIException

from ocdsextensionsdatacollector.babel_extractors import extract_codelist, extract_schema, extract_extension_meta


method_map = [
    ('**.csv', extract_codelist)
]

locale_dir = 'locale'
en_dir = 'en/LC_MESSAGES'

tx_endpoint = 'https://www.transifex.com'
tx_project = 'ocds-extensions'

try:
    TX_API_KEY = config('TX_API_KEY')
except UndefinedValueError:
    TX_API_KEY = None


def codelists_po(output_dir, extension_id, version):

    codelists_dir = os.path.join(
        output_dir, extension_id, version, 'codelists')

    if os.path.isdir(codelists_dir):

        po_dir = os.path.join(output_dir, locale_dir,
                              en_dir, extension_id, version)
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

                filepath = os.path.normpath(
                    os.path.join(codelists_dir, filename))
                catalog.add(message, None, [(filepath, lineno)],
                            auto_comments=comments, context=context)

        except CSVError as e:
            # TODO: fix this upstream in documentation-support or
            #       rewrite codelist csvs as part of data-collector download process
            print('Could not parse CSV for {}/{}: {}'.format(extension_id, version, e))

        output_file = os.path.join(po_dir, 'codelists.po')
        with open(output_file, 'wb') as outfile:

            write_po(outfile, catalog, width=76,
                     no_location=False,
                     omit_header=False,
                     sort_output=False,
                     sort_by_file=True,
                     include_lineno=True)


def schema_po(output_dir, extension_id, version):
    # TODO: check if they're always called release-schema.json. Maybe not?
    #       Shoudln't hard code this. Can there be more than one?
    schema_file = os.path.join(
        output_dir, extension_id, version, 'release-schema.json')
    po_dir = os.path.join(output_dir, locale_dir,
                          en_dir, extension_id, version)
    if not os.path.isdir(po_dir):
        os.makedirs(po_dir, exist_ok=True)

    catalog = Catalog(project=None,
                      version=None,
                      msgid_bugs_address=None,
                      copyright_holder=None,
                      charset='utf-8')

    messages = extract_from_file(extract_schema, schema_file)

    for lineno, message, comments, context in messages:
        catalog.add(message, None, [(schema_file, lineno)],
                    auto_comments=comments, context=context)

    output_file = os.path.join(po_dir, 'release-schema.po')
    with open(output_file, 'wb') as outfile:

        write_po(outfile, catalog, width=76,
                 no_location=False,
                 omit_header=False,
                 sort_output=False,
                 sort_by_file=True,
                 include_lineno=True)


def extension_po(output_dir, extension_id, version):
    extension_file = os.path.join(
        output_dir, extension_id, version, 'extension.json')
    po_dir = os.path.join(output_dir, locale_dir,
                          en_dir, extension_id, version)
    if not os.path.isdir(po_dir):
        os.makedirs(po_dir, exist_ok=True)

    catalog = Catalog(project=None,
                      version=None,
                      msgid_bugs_address=None,
                      copyright_holder=None,
                      charset='utf-8')

    messages = extract_from_file(extract_extension_meta, extension_file)

    for lineno, message, comments, context in messages:
        catalog.add(message, None, [(extension_file, lineno)],
                    auto_comments=comments, context=context)

    output_file = os.path.join(po_dir, 'extension.po')
    with open(output_file, 'wb') as outfile:

        write_po(outfile, catalog, width=76,
                 no_location=False,
                 omit_header=False,
                 sort_output=False,
                 sort_by_file=True,
                 include_lineno=True)


def docs_po(output_directory):
    current_directory = os.path.dirname(os.path.realpath(__file__))
    temp_i18n_directory = os.path.join(output_directory, 'temp_i18n')
    en_locale_directory = os.path.join(output_directory, locale_dir, en_dir)
    sphinx_extraction_logs = os.path.join(
        output_directory, 'sphinx_extraction_logs.txt')

    conf_directory = os.path.join(current_directory, 'sphinx_config')

    # have to make index file for sphinx to work
    index_file = os.path.join(conf_directory, 'index.md')
    shutil.copy(index_file, output_directory)

    # sphinx already prints output to a file, this just stops output to console
    fake_file = io.StringIO()
    with redirect_stdout(fake_file), redirect_stderr(fake_file):
        sphinx.build_main(['sphinx-build', '-b', 'gettext',
                           '-a',  # rebuild fully each time
                           '-w', sphinx_extraction_logs,  # log output file
                           '-c', conf_directory,
                           output_directory, temp_i18n_directory])

    os.remove(os.path.join(output_directory, 'index.md'))
    os.remove(os.path.join(temp_i18n_directory, 'index.pot'))

    for full_file_path in glob.glob(temp_i18n_directory + '/**/README.pot', recursive=True):
        new_relative_path = full_file_path[len(
            temp_i18n_directory) + 1:].replace('README.pot', 'docs.po')
        new_path = os.path.join(en_locale_directory, new_relative_path)
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        shutil.copy(full_file_path, new_path)

    shutil.rmtree(temp_i18n_directory)


def make_resource_slug(extension, version, po_file):
    # slugify strips '.' which garbles version numbers
    version = version.replace('.', '-')
    return slugify('{}-{}-{}'.format(extension, version, po_file.replace('.po', '')))


def get_resource_name(extension, version, po_file):
    return '{}/{}/{}'.format(extension, version, po_file.replace('.po', ''))


def list_translated_languages(resource_slug):
    if not TX_API_KEY:
        print('No Transifex API key - please set TX_API_KEY in .env')
        return

    tx_api = TransifexAPI('api', TX_API_KEY, tx_endpoint)
    print('Getting languages for {}'.format(resource_slug))
    return tx_api.list_languages(tx_project, resource_slug)


def get_from_transifex(output_dir, extension_id, version, po_file):
    if not TX_API_KEY:
        print('No Transifex API key - please set TX_API_KEY in .env')
        return

    tx_api = TransifexAPI('api', TX_API_KEY, tx_endpoint)
    resource_slug = make_resource_slug(extension_id, version, po_file)

    langs = list_translated_languages(resource_slug)
    for lang in langs:
        if 'en' not in lang.lower():
            save_path = os.path.join(
                            output_dir, locale_dir, lang, 'LC_MESSAGES', 
                            extension_id, version)
            if not os.path.isdir(save_path):
                os.makedirs(save_path, exist_ok=True)
            
            print('Getting {} for {}'.format(lang, resource_slug))
            tx_api.get_translation(tx_project, resource_slug, lang, os.path.join(save_path, po_file))


def send_to_transifex(po_file, resource_slug, resource_name):

    if not TX_API_KEY:
        print('No Transifex API key - please set TX_API_KEY in .env')
        return

    tx_api = TransifexAPI('api', TX_API_KEY, tx_endpoint)
    if tx_api.project_exists(tx_project):
        try:
            response = tx_api.new_resource(
                tx_project,
                po_file,
                resource_slug=resource_slug,
                resource_name=resource_name)
            print('Creating {} on transifex'.format(resource_name))
        except TransifexAPIException:
            response = tx_api.update_source_translation(
                tx_project,
                resource_slug,
                po_file)
            print('Updating {} on transifex'.format(resource_name))


def walk_po_files(output_dir, extension, version):
    source_po_dir = os.path.join(
        output_dir, locale_dir, en_dir, extension, version)

    file_path_slug_name = []

    for dir_name, subdirs, files in os.walk(source_po_dir):
        for filename in files:
            if filename.endswith('.po'):
                resource_slug = make_resource_slug(
                    extension, version, filename)
                resource_name = get_resource_name(extension, version, filename)
                po_file_path = os.path.join(source_po_dir, filename)

                file_path_slug_name.append(
                    (filename, po_file_path, resource_slug, resource_name))

    return file_path_slug_name


def delete_tx_resources(output_dir, extension, version):
    # For cleanup/debugging purposes
    source_po_dir = os.path.join(
        output_dir, locale_dir, en_dir, extension, version)

    for dir_name, subdirs, files in os.walk(source_po_dir):
        for filename in files:
            if filename.endswith('.po'):
                resource_slug = make_resource_slug(
                    extension, version, filename)
                tx_api = TransifexAPI('api', TX_API_KEY, tx_endpoint)
                print("Deleting {}".format(resource_slug))
                tx_api.delete_resource(tx_project, resource_slug)
