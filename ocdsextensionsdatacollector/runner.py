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
        if not os.path.isdir(self.output_directory):
            os.mkdir(self.output_directory)

    def run(self):

        out = {
            'extensions': {}
        }

        registry = ExtensionRegistry(self.extension_versions_data, self.extensions_data)

        for version in registry:
            if self.sample and len(out['extensions']) >= 5:
                continue

            # Part 1 : add  basic info to output
            if version.id not in out['extensions']:
                out['extensions'][version.id] = {
                    'versions': {},
                    'category': version.category,
                    'core': version.core
                }

            out['extensions'][version.id]['versions'][version.version] = {
                'date': version.date,
                'base_url': version.base_url,
                'download_url': version.download_url,
            }

            # Part 2: download the extension
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

            # Part 3 : add information from extension to output
            with open(os.path.join(version_output_dir, "extension.json")) as infile:
                extension_json = json.load(infile)
                out['extensions'][version.id]['versions'][version.version]['name'] = \
                    extension_json['name']
                out['extensions'][version.id]['versions'][version.version]['description'] = \
                    extension_json['description']

        with open(os.path.join(self.output_directory, "data.json"), "w") as outfile:
            json.dump(out, outfile, indent=4)
