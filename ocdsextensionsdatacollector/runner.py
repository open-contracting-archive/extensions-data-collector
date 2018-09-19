import os
import json
import requests
import zipfile
import io
import shutil
import copy
import csv
from collections import OrderedDict
from decouple import config, UndefinedValueError

from ocdsextensionregistry import ExtensionRegistry
from ocdsextensionsdatacollector.i18n_helpers import codelists_po, schema_po, docs_po, delete_tx_resources
from ocdsextensionsdatacollector.i18n_helpers import upload_po_files, download_po_files, translate

STANDARD_COMPATIBILITY_VERSIONS = ['1.1']


class Runner:

    def __init__(self, sample=False, output_directory=None,
                 extensions_data='https://raw.githubusercontent.com/open-contracting/extension_registry/master/extensions.csv',  # noqa
                 extension_versions_data='https://raw.githubusercontent.com/open-contracting/extension_registry/master/extension_versions.csv'  # noqa
                ):
        self.output_directory = output_directory or \
            os.path.join(os.path.dirname(
                os.path.realpath(__file__)), '..', 'output_dir')
        self.extensions_data = extensions_data
        self.extension_versions_data = extension_versions_data
        self.sample = sample
        self.out = None
        if not os.path.isdir(self.output_directory):
            os.mkdir(self.output_directory)

        try:
            self.tx_api_key = config('TX_API_KEY')
        except UndefinedValueError:
            self.tx_api_key = None

    def run(self):
        self.out = {
            'extensions': {}
        }

        registry = ExtensionRegistry(
            self.extension_versions_data, self.extensions_data)

        for version in registry:
            if self.sample and len(self.out['extensions']) >= 5:
                continue

            self._add_basic_info_to_output(version)
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

    def _add_basic_info_to_output(self, version):
        if version.id not in self.out['extensions']:
            self.out['extensions'][version.id] = {
                'versions': {},
                'category': version.category,
                'core': version.core,
                'main_version': None,
                'name': {},
                'description': {},
                'list_version_keys_all': []
            }

        self.out['extensions'][version.id]['versions'][version.version] = {
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
            'standard_compatibility': {}
        }
        for standard_version in STANDARD_COMPATIBILITY_VERSIONS:
            self.out['extensions'][version.id]['versions'][version.version]['standard_compatibility'][standard_version] = False  # noqa

    def _download_version(self, version):
        version_output_dir = os.path.join(
            self.output_directory, version.id, version.version)
        version_output_file = os.path.join(
            self.output_directory, version.id, version.version + '-status.json')

        if os.path.isfile(version_output_file):
            # We already have this download on disk!
            # We have to decide what to do, download it again?
            # For now, if it's core (and not master) we don't download. We trust them not to be re-releasing versions.
            if version.core and version.version != 'master':
                return
            # If it's not core, we always download as we can't trust it won't have changed.
            os.remove(version_output_file)

        # delete anything currently on disk - we think it's old
        # (or it's possible it's a half complete download and we want to start again)
        if os.path.isdir(version_output_dir):
            shutil.rmtree(version_output_dir)

        # download contents and save to disk
        os.makedirs(version_output_dir)
        response = requests.get(version.download_url, allow_redirects=True)
        response.raise_for_status()
        version_zipfile = zipfile.ZipFile(io.BytesIO(response.content))
        names = version_zipfile.namelist()
        start = len(names[0])
        for name in names[1:]:
            if name[-1:] == '/':
                os.makedirs(os.path.join(version_output_dir, name[start:]))
            else:
                with open(os.path.join(version_output_dir, name[start:]), "wb") as outfile:
                    outfile.write(version_zipfile.read(name))

        # Finally, write status file to indicate a successful download
        out_status = {
            # This is in case in the future we change how downloads work,
            # and need to know if something on disk is from the old or new code.
            'disk_data_layout_version': 1
        }
        with open(version_output_file, "w") as outfile:
            json.dump(out_status, outfile, indent=4)

    def _add_information_from_download_to_output(self, version):
        self._add_information_from_download_to_output_extension_json(version)
        self._add_information_from_download_to_output_release_schema(version)
        self._add_information_from_download_to_output_record_package_schema(
            version)
        self._add_information_from_download_to_output_release_package_schema(
            version)
        self._add_information_from_download_to_output_record_codelists(version)
        self._add_information_from_download_to_output_record_docs(version)
        self._add_information_from_download_to_output_record_readme(version)

    def _add_information_from_download_to_output_extension_json(self, version, language='en'):
        if language == 'en':
            version_output_dir = os.path.join(
                self.output_directory, version.id, version.version)
        else:
            version_output_dir = os.path.join(
                self.output_directory, language, version.id, version.version)

        with open(os.path.join(version_output_dir, "extension.json")) as infile:
            extension_json = self._normalise_extension_json(json.load(infile))
            
            self.out['extensions'][version.id]['versions'][version.version][language] = {
                'name': extension_json['name']
            }
            self.out['extensions'][version.id]['versions'][version.version][language] = {
                'description': extension_json['description']
            }
            
            for c_v in STANDARD_COMPATIBILITY_VERSIONS:
                if c_v in extension_json['compatibility']:
                    self.out['extensions'][version.id]['versions'][version.version]['standard_compatibility'][c_v] = \
                        True

    def _add_information_from_download_to_output_release_schema(self, version, language='en'):
        if language == 'en':
            version_output_dir = os.path.join(
                self.output_directory, version.id, version.version)
        else:
            version_output_dir = os.path.join(
                self.output_directory, language, version.id, version.version)

        release_schema_filename = os.path.join(
            version_output_dir, "release-schema.json")
        if os.path.isfile(release_schema_filename):

            with open(release_schema_filename) as infile:
                try:
                    file_json = json.load(infile)
                    if self.out['extensions'][version.id]['versions'][version.version]['release_schema'] is not None:
                        self.out['extensions'][version.id]['versions'][version.version]['release_schema'][language] = file_json
                    else:
                        self.out['extensions'][version.id]['versions'][version.version]['release_schema'] = {
                            language: file_json
                        }
                except json.decoder.JSONDecodeError as error:
                    self.out['extensions'][version.id]['versions'][version.version]['errors'].append({
                        'message': 'Error while trying to parse release-schema.json: ' + error.msg
                    })

    def _add_information_from_download_to_output_record_package_schema(self, version, language='en'):
        if language == 'en':
            version_output_dir = os.path.join(
                self.output_directory, version.id, version.version)
        else:
            version_output_dir = os.path.join(
                self.output_directory, language, version.id, version.version)

        record_package_schema_filename = os.path.join(
            version_output_dir, "record-package-schema.json")
        if os.path.isfile(record_package_schema_filename):
            with open(record_package_schema_filename) as infile:
                try:
                    file_json = json.load(infile)
                    
                    if self.out['extensions'][version.id]['versions'][version.version]['record_package_schema'] is not None:
                        self.out['extensions'][version.id]['versions'][version.version]['record_package_schema'][language] = file_json
                    else:
                        self.out['extensions'][version.id]['versions'][version.version]['record_package_schema'] = {
                            language: file_json
                        }

                except json.decoder.JSONDecodeError as error:
                    self.out['extensions'][version.id]['versions'][version.version]['errors'].append({
                        'message': 'Error while trying to parse record-package-schema.json: ' + error.msg
                    })

    def _add_information_from_download_to_output_release_package_schema(self, version, language='en'):
        if language == 'en':
            version_output_dir = os.path.join(
                self.output_directory, version.id, version.version)
        else:
            version_output_dir = os.path.join(
                self.output_directory, language, version.id, version.version)

        release_package_schema_filename = os.path.join(
            version_output_dir, "release-package-schema.json")

        if os.path.isfile(release_package_schema_filename):
            with open(release_package_schema_filename) as infile:
                try:
                    file_json = json.load(infile)
                    if self.out['extensions'][version.id]['versions'][version.version]['release_package_schema'] is not None:
                        self.out['extensions'][version.id]['versions'][version.version]['release_package_schema'][language] = file_json
                    else:
                        self.out['extensions'][version.id]['versions'][version.version]['release_package_schema'] = {
                            language: file_json
                        }
                except json.decoder.JSONDecodeError as error:
                    self.out['extensions'][version.id]['versions'][version.version]['errors'].append({
                        'message': 'Error while trying to parse release-package-schema.json: ' + error.msg
                    })

    def _add_information_from_download_to_output_record_codelists(self, version, language='en'):
        if language == 'en':
            version_output_dir = os.path.join(
                self.output_directory, version.id, version.version)
        else:
            version_output_dir = os.path.join(
                self.output_directory, language, version.id, version.version)

        codelists_dir_name = os.path.join(version_output_dir, "codelists")
        if os.path.isdir(codelists_dir_name):

            names = [f for f in os.listdir(codelists_dir_name) if os.path.isfile(
                os.path.join(codelists_dir_name, f))]
            for name in names:

                data = {'items': {}, 'fieldnames': OrderedDict()}

                existing_items = self.out.get('extensions', {}).get(version.id, {}).get(
                    'versions', {}).get(version.version, {}).get('codelists', {}).get(name)

                if existing_items is not None:
                    if existing_items.get('items') is not None:
                        data['items'] = existing_items['items']
                    if existing_items.get('fieldnames') is not None:
                        data['fieldnames'] = existing_items['fieldnames']

                with open(os.path.join(codelists_dir_name, name), 'r') as csvfile:
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
                        print('Code not found in {}'.format(
                            data['fieldnames']))

                    # And use the translated headers to map the translated values onto
                    # translated keys in the output
                    for row in reader:
                        if code_header in row:
                            code = row[code_header]
                            del row[code_header]
                            if code:
                                try:
                                    data['items'][code][language] = row
                                except KeyError:
                                    data['items'][code] = {
                                        language: row
                                    }

                self.out['extensions'][version.id]['versions'][version.version]['codelists'][name] = data

    def _add_information_from_download_to_output_record_docs(self, version):
        version_output_dir = os.path.join(
            self.output_directory, version.id, version.version)
        docs_dir_name = os.path.join(version_output_dir, "docs")
        if os.path.isdir(docs_dir_name):
            names = [f for f in os.listdir(docs_dir_name) if os.path.isfile(
                os.path.join(docs_dir_name, f))]
            for name in names:
                with open(os.path.join(docs_dir_name, name), 'r') as docfile:
                    self.out['extensions'][version.id]['versions'][version.version]['docs'][name] = {
                        "en": {
                            "content": docfile.read()
                        }
                    }

    def _add_information_from_download_to_output_record_readme(self, version):
        version_output_dir = os.path.join(
            self.output_directory, version.id, version.version)
        for name in ['README.md', 'readme.md']:
            readme_file_name = os.path.join(version_output_dir, name)
            if os.path.isfile(readme_file_name):
                with open(readme_file_name, 'r') as readmefile:
                    self.out['extensions'][version.id]['versions'][version.version]['readme'] = {
                        "en": {
                            "content": readmefile.read(),
                            "type": "markdown"
                        }
                    }
                    return

    # This def is a candidate for pushing upstream to extension_registry.py
    def _normalise_extension_json(self, in_extension_json):
        # TODO: i18n here
        out_extension_json = copy.deepcopy(in_extension_json)

        if out_extension_json['name'] and isinstance(out_extension_json['name'], str):
            out_extension_json['name'] = {
                'en': out_extension_json['name']
            }
        if out_extension_json['description'] and isinstance(out_extension_json['description'], str):
            out_extension_json['description'] = {
                'en': out_extension_json['description']
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
        all_version_keys = list(
            self.out['extensions'][extension_id]['versions'].keys())

        all_version_keys.sort()
        # TODO sort all_version_keys better here

        self.out['extensions'][extension_id]['list_version_keys_all'] = all_version_keys

    def _do_translations(self, registry):

        # Make EN .po files for all extension docs
        docs_po(self.output_directory)

        for extension in registry:

            # Make EN .po files for codelists and schema
            codelists_po(self.output_directory,
                         extension.id, extension.version)
            schema_po(self.output_directory, extension.id, extension.version)

            # Upload EN files to transifex
            # Files in output_dir/locale/en/LC_MESSAGES/{extension}/{version}/*.po
            #  are posted to the transifex API
            upload_po_files(self.output_directory, extension.id,
                            extension.version, self.tx_api_key)

            # Download translations
            # Translations from transifex are saved in
            #  output_dir/locale/{lang}/LC_MESSAGES/{extension}/{version}/*.po
            download_po_files(self.output_directory, extension.id,
                              extension.version, self.tx_api_key)

            # Do translations
            # .po files are compiled to .mo files and used to generate translated
            #  files in output_dir/{lang}/LC_MESSAGES/{extension}/{version}/
            # TODO: We don't need to keep the translations around, delete them after?
            languages = translate(self.output_directory,
                                  extension.id, extension.version)

            # Add translations to self.out
            for language in languages:
                if language != 'en':
                    self._add_information_from_download_to_output_record_codelists(
                        extension, language)
                    # TODO: self._add_information_from_download_to_output_extension_json(extension, language)
                    self._add_information_from_download_to_output_release_schema(extension, language)
                    self._add_information_from_download_to_output_record_package_schema(extension, language)
                    self._add_information_from_download_to_output_release_package_schema(extension, language)
                    # TODO: readme
                    # TODO: docs

    def _write_output(self):
        with open(os.path.join(self.output_directory, "data.json"), "w") as outfile:
            json.dump(self.out, outfile, indent=4)
