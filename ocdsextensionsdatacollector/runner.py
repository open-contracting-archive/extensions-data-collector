import os
import json
import requests
import zipfile
import io

from ocdsextensionregistry import ExtensionRegistry


class Runner:

    def __init__(self, sample=False):
        self.output_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'output_dir')
        self.extensions_data = 'https://raw.githubusercontent.com/open-contracting/extension_registry/master/extensions.csv' # noqa
        self.extension_versions_data = 'https://raw.githubusercontent.com/open-contracting/extension_registry/master/extension_versions.csv'  # noqa
        self.sample = sample
        self.out = None
        if not os.path.isdir(self.output_directory):
            os.mkdir(self.output_directory)

    def run(self):
        self.out = {
            'extensions': {}
        }

        registry = ExtensionRegistry(self.extension_versions_data, self.extensions_data)

        for version in registry:
            if self.sample and len(self.out['extensions']) >= 5:
                continue

            self._add_basic_info_to_output(version)
            self._download_version(version)
            self._add_information_from_download_to_output(version)

        self._write_output()

    def _add_basic_info_to_output(self, version):
        if version.id not in self.out['extensions']:
            self.out['extensions'][version.id] = {
                'versions': {},
                'category': version.category,
                'core': version.core
            }

        self.out['extensions'][version.id]['versions'][version.version] = {
            'date': version.date,
            'base_url': version.base_url,
            'download_url': version.download_url,
        }

    def _download_version(self, version):
        version_output_dir = os.path.join(self.output_directory, version.id, version.version)
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

    def _add_information_from_download_to_output(self, version):
        version_output_dir = os.path.join(self.output_directory, version.id, version.version)
        with open(os.path.join(version_output_dir, "extension.json")) as infile:
            extension_json = json.load(infile)
            self.out['extensions'][version.id]['versions'][version.version]['name'] = \
                extension_json['name']
            self.out['extensions'][version.id]['versions'][version.version]['description'] = \
                extension_json['description']

    def _write_output(self):
        with open(os.path.join(self.output_directory, "data.json"), "w") as outfile:
            json.dump(self.out, outfile, indent=4)
