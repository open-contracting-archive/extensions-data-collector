import os
import json
import requests
import zipfile
import io
import shutil

from ocdsextensionregistry import ExtensionRegistry


class Runner:

    def __init__(self, sample=False, output_directory=None,
                 extensions_data='https://raw.githubusercontent.com/open-contracting/extension_registry/master/extensions.csv',  # noqa
                 extension_versions_data='https://raw.githubusercontent.com/open-contracting/extension_registry/master/extension_versions.csv'  # noqa
                ):
        self.output_directory = output_directory or \
                                os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'output_dir')
        self.extensions_data = extensions_data
        self.extension_versions_data = extension_versions_data
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
        version_output_file = os.path.join(self.output_directory, version.id, version.version + '-status.json')

        if os.path.isfile(version_output_file):
            # We already have this download on disk!
            # We have to decide what to do, download it again?
            # For now, if it's core we don't download. Core is meant to be frozen once released.
            if version.core:
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
