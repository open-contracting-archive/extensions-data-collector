import copy
import csv
import io
import json
import os
import shutil
import zipfile
from collections import OrderedDict
from pathlib import Path

import requests

from ocdsextensionregistry import ExtensionRegistry
from ocdsextensionsdatacollector.i18n_helpers import codelists_po, schema_po, docs_po
from ocdsextensionsdatacollector.i18n_helpers import upload_po_files, download_po_files, translate, locale_dir

STANDARD_COMPATIBILITY_VERSIONS = ['1.1']


class Runner:
    def __init__(self, output_directory, limit=None, tx_api_key=None,
                 extensions_data='https://raw.githubusercontent.com/open-contracting/extension_registry/master/extensions.csv',  # noqa
                 extension_versions_data='https://raw.githubusercontent.com/open-contracting/extension_registry/master/extension_versions.csv'  # noqa
                ):
        self.output_directory = Path(output_directory)
        self.limit = limit
        self.tx_api_key = tx_api_key
        self.extensions_data = extensions_data
        self.extension_versions_data = extension_versions_data
        self.out = None
        if not self.output_directory.is_dir():
            self.output_directory.mkdir()

    def run(self):
        self.out = {
            'extensions': {}
        }

        registry = ExtensionRegistry(self.extension_versions_data, self.extensions_data)

        for version in registry:
            if self.limit and len(self.out['extensions']) >= self.limit:
                break

            self._add_registry_metadata_to_output(version)
            self._download_version(version)
            self._add_information_from_download_to_output(version)

        for extension_id in self.out['extensions'].keys():
            self._add_information_from_version_to_extension(
                extension_id,
                self._get_main_version_for_extension(extension_id)
            )
            self._add_version_key_lists_to_extension(extension_id)

        if self.tx_api_key is not None:
            self._do_translations(registry)

        self._write_output()

    def _add_registry_metadata_to_output(self, version):
        extensions_obj = self.out['extensions']
        if version.id not in extensions_obj:
            extensions_obj[version.id] = {
                'versions': {},
                'category': version.category,
                'core': version.core,
                'main_version': None,
                'name': {},
                'description': {},
                'list_version_keys_all': [],
            }

        extensions_obj[version.id]['versions'][version.version] = {
            'date': version.date,
            'base_url': version.base_url,
            'download_url': version.download_url,
            'release_schema': None,
            'record_package_schema': None,
            'release_package_schema': None,
            'errors': [],
            'codelists': {},
            'docs': {},
            'readme': None,
            'name': {},
            'description': {},
            'standard_compatibility': {},
        }

        for standard_version in STANDARD_COMPATIBILITY_VERSIONS:
            extensions_obj[version.id]['versions'][version.version]['standard_compatibility'][standard_version] = False

    def _download_version(self, version):
        version_output_dir = self.output_directory / version.id / version.version
        version_output_file = self.output_directory / version.id / '{}-status.json'.format(version.version)

        # Trust that frozen versions of core extensions don't change.
        if version_output_file.is_file() and version_output_dir.is_dir() and version.core and version.version != 'master':
            return

        if version_output_file.is_file():
            version_output_file.unlink()

        if version_output_dir.is_dir():
            shutil.rmtree(version_output_dir)

        version_output_dir.mkdir(parents=True)
        response = requests.get(version.download_url, allow_redirects=True)
        response.raise_for_status()
        version_zipfile = zipfile.ZipFile(io.BytesIO(response.content))
        names = version_zipfile.namelist()
        start = len(names[0])
        for name in names[1:]:
            if name[-1:] == '/':
                (version_output_dir / name[start:]).mkdir(parents=True)
            else:
                with (version_output_dir / name[start:]).open('wb') as outfile:
                    outfile.write(version_zipfile.read(name))

        # Finally, write status file to indicate a successful download
        out_status = {
            # This is in case in the future we change how downloads work,
            # and need to know if something on disk is from the old or new code.
            'disk_data_layout_version': 1
        }
        with version_output_file.open('w') as outfile:
            json.dump(out_status, outfile, indent=4)

    def _add_information_from_download_to_output(self, version):
        self._add_information_from_download_to_output_extension_json(version)
        self._add_information_from_download_to_output_release_schema(version)
        self._add_information_from_download_to_output_record_package_schema(version)
        self._add_information_from_download_to_output_release_package_schema(version)
        self._add_information_from_download_to_output_record_codelists(version)
        self._add_information_from_download_to_output_record_docs(version)
        self._add_information_from_download_to_output_record_readme(version)

    def _add_information_from_download_to_output_extension_json(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        with (version_output_dir / 'extension.json').open() as infile:
            extension_json = self._normalise_extension_json(json.load(infile), language=language)

            for field in ('name', 'description'):
                version_object = self.out['extensions'][version.id]['versions'][version.version]
                language_object = version_object.get(field) or {}
                version_object[field] = language_object
                language_object[language] = extension_json[field][language]

            for c_v in STANDARD_COMPATIBILITY_VERSIONS:
                if c_v in extension_json['compatibility']:
                    self.out['extensions'][version.id]['versions'][version.version]['standard_compatibility'][c_v] = \
                        True

    def _add_information_from_download_to_output_release_schema(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        release_schema_filename = version_output_dir / 'release-schema.json'
        if release_schema_filename.is_file():
            with release_schema_filename.open() as infile:
                try:
                    version_obj = self.out['extensions'][version.id]['versions'][version.version]
                    file_json = json.load(infile)
                    if version_obj['release_schema'] is not None:
                        version_obj['release_schema'][language] = file_json
                    else:
                        version_obj['release_schema'] = {
                            language: file_json
                        }
                except json.decoder.JSONDecodeError as error:
                    version_obj['errors'].append({
                        'message': 'Error while trying to parse release-schema.json: ' + error.msg
                    })

    def _add_information_from_download_to_output_record_package_schema(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        record_package_schema_filename = version_output_dir / 'record-package-schema.json'
        if record_package_schema_filename.is_file():
            with record_package_schema_filename.open() as infile:
                try:
                    version_obj = self.out['extensions'][version.id]['versions'][version.version]
                    file_json = json.load(infile)
                    if version_obj['record_package_schema'] is not None:
                        version_obj['record_package_schema'][language] = file_json
                    else:
                        version_obj['record_package_schema'] = {
                            language: file_json
                        }

                except json.decoder.JSONDecodeError as error:
                    version_obj['errors'].append({
                        'message': 'Error while trying to parse record-package-schema.json: ' + error.msg
                    })

    def _add_information_from_download_to_output_release_package_schema(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        release_package_schema_filename = version_output_dir / 'release-package-schema.json'

        if release_package_schema_filename.is_file():
            with release_package_schema_filename.open() as infile:
                try:
                    version_obj = self.out['extensions'][version.id]['versions'][version.version]
                    file_json = json.load(infile)
                    if version_obj['release_package_schema'] is not None:
                        version_obj['release_package_schema'][language] = file_json
                    else:
                        version_obj['release_package_schema'] = {
                            language: file_json
                        }
                except json.decoder.JSONDecodeError as error:
                    version_obj['errors'].append({
                        'message': 'Error while trying to parse release-package-schema.json: ' + error.msg
                    })

    def _add_information_from_download_to_output_record_codelists(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        codelists_dir_name = version_output_dir / 'codelists'
        if codelists_dir_name.is_dir():
            names = [f for f in codelists_dir_name.iterdir() if (codelists_dir_name / f).is_file()]
            for name in names:
                data = {'items': {}, 'fieldnames': OrderedDict()}

                existing_items = self.out.get('extensions', {}).get(version.id, {}).get(
                    'versions', {}).get(version.version, {}).get('codelists', {}).get(name)

                if existing_items is not None:
                    if existing_items.get('items') is not None:
                        data['items'] = existing_items['items']
                    if existing_items.get('fieldnames') is not None:
                        data['fieldnames'] = existing_items['fieldnames']

                with (codelists_dir_name / name).open() as csvfile:
                    reader = csv.DictReader(csvfile)

                    # Extract the csv headers from the EN version to use as canonical
                    # keys to reference the codes
                    if language == 'en':
                        fieldnames = reader.fieldnames
                        for fieldname in fieldnames:
                            try:
                                data['fieldnames'][fieldname]['en'] = fieldname
                            except KeyError:
                                data['fieldnames'][fieldname] = {
                                    'en': fieldname
                                }
                    else:
                        # And assume the translated headers will be in the same order as EN
                        fieldnames = reader.fieldnames
                        en_fieldnames = list(data['fieldnames'].keys())

                        for index, fieldname in enumerate(fieldnames):
                            key = en_fieldnames[index]
                            data['fieldnames'][key][language] = fieldname

                    # Now we can look up the translated header by the EN key
                    try:
                        code_header = data['fieldnames']['Code'][language]
                    except KeyError:
                        print('Code not found in {}'.format(data['fieldnames']))

                    # And use the translated headers to map the translated values onto
                    # translated keys in the output
                    for row in reader:
                        if code_header in row:
                            code = row[code_header]
                            if code:
                                try:
                                    data['items'][code][language] = row
                                except KeyError:
                                    data['items'][code] = {
                                        language: row
                                    }

                self.out['extensions'][version.id]['versions'][version.version]['codelists'][name] = data

    def _add_information_from_download_to_output_record_docs(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        docs_dir_name = version_output_dir / 'docs'
        if docs_dir_name.is_dir():
            names = [f for f in docs_dir_name.iterdir() if (docs_dir_name / f).is_file()]
            for name in names:
                with (docs_dir_name / name).open() as docfile:
                    docs_object = self.out['extensions'][version.id]['versions'][version.version]['docs']
                    doc_object = docs_object.get(name) or {}
                    docs_object[name] = docs_object
                    docs_object[language] = {
                        "content": docfile.read()
                    }

    def _add_information_from_download_to_output_record_readme(self, version, language='en'):
        version_output_dir = self._get_version_output_dir(version, language)

        for name in ['README.md', 'readme.md']:
            readme_file_name = version_output_dir / name
            if readme_file_name.is_file():
                with readme_file_name.open() as readmefile:
                    version_object = self.out['extensions'][version.id]['versions'][version.version]
                    readme_object = version_object.get('readme') or {}
                    version_object['readme'] = readme_object
                    readme_object[language] = {
                        "content": readmefile.read(),
                        "type": "markdown"
                    }
                    return

    def _get_version_output_dir(self, version, language):
        if language == 'en':
            return self.output_directory / version.id / version.version
        else:
            return self.output_directory / locale_dir / language / 'TRANSLATIONS' / version.id / version.version

    # This def is a candidate for pushing upstream to extension_registry.py
    def _normalise_extension_json(self, in_extension_json, language='en'):
        out_extension_json = copy.deepcopy(in_extension_json)

        if out_extension_json['name'] and isinstance(out_extension_json['name'], str):
            out_extension_json['name'] = {
                language: out_extension_json['name']
            }
        if out_extension_json['description'] and isinstance(out_extension_json['description'], str):
            out_extension_json['description'] = {
                language: out_extension_json['description']
            }
        if 'compatibility' not in out_extension_json or isinstance(out_extension_json['compatibility'], str):
            # Historical data - Assume it's compatible with earliest version that had extensions.
            out_extension_json['compatibility'] = ['1.1']

        return out_extension_json

    def _get_main_version_for_extension(self, extension_id):
        if 'master' in self.out['extensions'][extension_id]['versions'].keys():
            return 'master'
        else:
            # In theory, there may be an extension published without the 'master' version.
            # It hasn't happened yet!
            # When it does, we need to pick the latest version here and call the function with that.
            raise Exception

    def _add_information_from_version_to_extension(self, extension_id, version_id):
        self.out['extensions'][extension_id]['main_version'] = version_id
        self.out['extensions'][extension_id]['name'] = \
            self.out['extensions'][extension_id]['versions'][version_id]['name']
        self.out['extensions'][extension_id]['description'] = \
            self.out['extensions'][extension_id]['versions'][version_id]['description']

    def _add_version_key_lists_to_extension(self, extension_id):
        all_version_keys = list(self.out['extensions'][extension_id]['versions'].keys())

        all_version_keys.sort()
        # TODO sort all_version_keys better here

        self.out['extensions'][extension_id]['list_version_keys_all'] = all_version_keys

    def _do_translations(self, registry):

        # Make EN .po files for all extension docs
        docs_po(self.output_directory)

        for extension in registry:

            # Make EN .po files for codelists and schema
            codelists_po(self.output_directory, extension.id, extension.version)
            schema_po(self.output_directory, extension.id, extension.version)

            # Upload EN files to transifex
            # Files in output_dir/locale/en/LC_MESSAGES/{extension}/{version}/*.po
            #  are posted to the transifex API
            upload_po_files(self.output_directory, extension.id, extension.version, self.tx_api_key)

            # Download translations
            # Translations from transifex are saved in
            #  output_dir/locale/{lang}/LC_MESSAGES/{extension}/{version}/*.po
            download_po_files(self.output_directory, extension.id, extension.version, self.tx_api_key)

            # Do translations
            # .po files are compiled to .mo files and used to generate translated
            #  files in output_dir/{lang}/LC_MESSAGES/{extension}/{version}/
            # TODO: We don't need to keep the translations around, delete them after?
            languages = translate(self.output_directory, extension.id, extension.version)

            # Add translations to self.out
            for language in languages:
                if language != 'en':
                    self._add_information_from_download_to_output_extension_json(extension, language)
                    self._add_information_from_download_to_output_release_schema(extension, language)
                    self._add_information_from_download_to_output_record_package_schema(extension, language)
                    self._add_information_from_download_to_output_release_package_schema(extension, language)
                    self._add_information_from_download_to_output_record_codelists(extension, language)
                    self._add_information_from_download_to_output_record_docs(extension, language)
                    self._add_information_from_download_to_output_record_readme(extension, language)

    def _write_output(self):
        with (self.output_directory / 'data.json').open('w') as outfile:
            json.dump(self.out, outfile, indent=4)
