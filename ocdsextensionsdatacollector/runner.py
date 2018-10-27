import json
from pathlib import Path

from ocdsextensionregistry import ExtensionRegistry
from ocdsextensionsdatacollector.i18n_helpers import codelists_po, schema_po, docs_po
from ocdsextensionsdatacollector.i18n_helpers import upload_po_files, download_po_files, translate
from ocdsextensionsdatacollector.version_data_collector import VersionDataCollector


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

            if version.id not in self.out['extensions']:
                self.out['extensions'][version.id] = {
                    'versions': {},
                    'category': version.category,
                    'core': version.core,
                    'main_version': None,
                    'name': {},
                    'description': {},
                    'list_version_keys_all': [],
                }

            collector = VersionDataCollector(self.output_directory, version)
            self.out['extensions'][version.id]['versions'][version.version] = collector.collect()

        for extension_id in self.out['extensions'].keys():
            main_version = self._get_main_version_for_extension(extension_id)
            self._add_information_from_version_to_extension(extension_id, main_version)
            self._add_version_key_lists_to_extension(extension_id)

        if self.tx_api_key is not None:
            self._do_translations(registry)

        self._write_output()

    def _get_main_version_for_extension(self, extension_id):
        if 'master' in self.out['extensions'][extension_id]['versions'].keys():
            return 'master'
        else:
            # In theory, there may be an extension published without the 'master' version.
            # It hasn't happened yet!
            # When it does, we need to pick the latest version here and call the function with that.
            raise Exception

    def _add_information_from_version_to_extension(self, extension_id, version_id):
        extension_obj = self.out['extensions'][extension_id]
        extension_obj['main_version'] = version_id
        extension_obj['name'] = extension_obj['versions'][version_id]['name']
        extension_obj['description'] = extension_obj['versions'][version_id]['description']

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
        with (self.output_directory / 'data.json').open('w') as f:
            json.dump(self.out, f, indent=4)
