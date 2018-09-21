import glob
import io
import os
import polib
import shutil
import sphinx
from _csv import Error as CSVError
from contextlib import redirect_stdout, redirect_stderr

from babel.messages.catalog import Catalog
from babel.messages.extract import extract_from_dir
from babel.messages.pofile import write_po
from transifex.api import TransifexAPI
from transifex.util import slugify
from transifex.exceptions import TransifexAPIException

from ocdsextensionsdatacollector.babel_extractors import extract_codelist, extract_json
from ocdsextensionsdatacollector.translation import translate_codelists, translate_schema, translate_extension, translate_docs


method_map = [
    ('*.csv', extract_codelist),
    ('*.json', extract_json)
]

locale_dir = 'locale'
en_dir = 'en/LC_MESSAGES'

tx_endpoint = 'https://www.transifex.com'
tx_project = 'ocds-extensions'


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
    # Extracts all json files into one schema.po file
    # (including extension.json)
    schema_dir = os.path.join(output_dir, extension_id, version)
    po_dir = os.path.join(output_dir, locale_dir,
                          en_dir, extension_id, version)
    if not os.path.isdir(po_dir):
        os.makedirs(po_dir, exist_ok=True)

    catalog = Catalog(project=None,
                      version=None,
                      msgid_bugs_address=None,
                      copyright_holder=None,
                      charset='utf-8')

    messages = extract_from_dir(schema_dir, method_map)

    for filename, lineno, message, comments, context in messages:

        filepath = os.path.normpath(os.path.join(schema_dir, filename))
        catalog.add(message, None, [(filepath, lineno)],
                    auto_comments=comments, context=context)

    output_file = os.path.join(po_dir, 'schema.po')
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


def list_translated_languages(resource_slug, tx_api_key):
    tx_api = TransifexAPI('api', tx_api_key, tx_endpoint)
    return tx_api.list_languages(tx_project, resource_slug)


def list_lang_dirs(output_dir):
    langs = []
    translations_dir = os.path.join(output_dir, locale_dir)
    for subdir in os.listdir(translations_dir):
        if os.path.isdir(os.path.join(translations_dir, subdir)):
            langs.append(subdir)

    return langs


def get_from_transifex(output_dir, extension_id, version, po_file, tx_api_key):
    tx_api = TransifexAPI('api', tx_api_key, tx_endpoint)
    resource_slug = make_resource_slug(extension_id, version, po_file)

    langs = list_translated_languages(resource_slug, tx_api_key)
    for lang in langs:
        if 'en' not in lang.lower():
            save_path = os.path.join(
                output_dir, locale_dir, lang, 'LC_MESSAGES',
                extension_id, version)
            if not os.path.isdir(save_path):
                os.makedirs(save_path, exist_ok=True)

            print('Getting {} for {}'.format(lang, resource_slug))
            tx_api.get_translation(
                tx_project, resource_slug, lang, os.path.join(save_path, po_file))


def send_to_transifex(po_file, resource_slug, resource_name, tx_api_key):

    tx_api = TransifexAPI('api', tx_api_key, tx_endpoint)
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


def upload_po_files(output_dir, extension, version, tx_api_key):
    source_po_dir = os.path.join(
        output_dir, locale_dir, en_dir, extension, version)

    for dir_name, subdirs, files in os.walk(source_po_dir):
        for filename in files:
            if filename.endswith('.po'):
                resource_slug = make_resource_slug(
                    extension, version, filename)
                resource_name = get_resource_name(extension, version, filename)
                po_file_path = os.path.join(source_po_dir, filename)

                send_to_transifex(po_file_path, resource_slug,
                                  resource_name, tx_api_key)


def download_po_files(output_dir, extension, version, tx_api_key):
    source_po_dir = os.path.join(
        output_dir, locale_dir, en_dir, extension, version)
    for dir_name, subdirs, files in os.walk(source_po_dir):
        for filename in files:
            if filename.endswith('.po'):
                get_from_transifex(output_dir, extension,
                                   version, filename, tx_api_key)


def delete_tx_resources(output_dir, extension, version, tx_api_key):
    # For cleanup/debugging purposes
    source_po_dir = os.path.join(
        output_dir, locale_dir, en_dir, extension, version)

    # files = ['release-schema.po', 'extension.po']
    for dir_name, subdirs, files in os.walk(source_po_dir):
        for filename in files:
            if filename.endswith('.po'):
                resource_slug = make_resource_slug(
                    extension, version, filename)
                tx_api = TransifexAPI('api', tx_api_key, tx_endpoint)
                print("Deleting {}".format(resource_slug))
                try:
                    tx_api.delete_resource(tx_project, resource_slug)
                except TransifexAPIException:
                    pass


def translate(output_dir, extension, version):
    domains = {  # Path between LC_MESSAGES and the .po files
        'codelists': '{}/{}/codelists'.format(extension, version),
        'schema': '{}/{}/schema'.format(extension, version),
        'extension': '{}/{}/extension'.format(extension, version),
        'docs': '{}/{}/docs'.format(extension, version)
    }

    source_dir = os.path.join(output_dir, extension, version)
    locale_path = os.path.join(output_dir, locale_dir)
    langs = list_lang_dirs(output_dir)
    for language in langs:
        if 'en' not in language:
            # build_dir is temporary and should be deleted?
            # .. we don't need to keep the translated JSON etc around
            # unless we want to hook this up to the backups at some point
            build_dir = os.path.join(output_dir, language, extension, version)
            if not os.path.isdir(build_dir):
                os.makedirs(build_dir, exist_ok=True)

            # Translate codelists
            po_path = os.path.join(
                locale_path, language, 'LC_MESSAGES', '{}.po'.format(domains['codelists']))
            if os.path.isfile(po_path):
                po = polib.pofile(po_path)
                po.save_as_mofile(po_path[:-3] + '.mo')
                translate_codelists(
                    domains['codelists'],
                    os.path.join(source_dir, 'codelists'),
                    os.path.join(build_dir, 'codelists'),
                    locale_path, language)

            # Translate schema
            po_path = os.path.join(
                locale_path, language, 'LC_MESSAGES', '{}.po'.format(domains['schema']))
            schema_filenames = ['record-package-schema.json', 'release-package-schema.json', 'release-schema.json']
            filenames = [f for f in schema_filenames if os.path.isfile(os.path.join(source_dir, f))]
            if os.path.isfile(po_path):
                po = polib.pofile(po_path)
                po.save_as_mofile(po_path[:-3] + '.mo')
                translate_schema(
                    domains['schema'], filenames, source_dir, build_dir, locale_path, language, version)
                translate_extension(
                    domains['schema'], source_dir, build_dir, locale_path, language)

            po_path = os.path.join(
                locale_path, language, 'LC_MESSAGES', '{}.po'.format(domains['docs']))

            if os.path.isfile(po_path):
                po = polib.pofile(po_path)
                po.save_as_mofile(po_path[:-3] + '.mo')
                translate_docs(
                    domains['docs'], source_dir, build_dir, locale_path, language, extension, version)


    return langs
