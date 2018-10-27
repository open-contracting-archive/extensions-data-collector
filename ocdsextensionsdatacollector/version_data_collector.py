import copy
import csv
import io
import json
import shutil
import zipfile
from collections import OrderedDict, defaultdict
from pathlib import Path

import requests

from ocdsextensionsdatacollector.i18n_helpers import locale_dir

STANDARD_COMPATIBILITY_VERSIONS = ['1.1']


class VersionDataCollector:
    def __init__(self, output_directory, version):
        self.output_directory = Path(output_directory)
        self.version = version
        self.out = None

    def collect(self):
        self.out = {
            'date': self.version.date,
            'base_url': self.version.base_url,
            'download_url': self.version.download_url,
            'release_schema': {},  # language map
            'record_package_schema': {},  # language map
            'release_package_schema': {},  # language map
            'errors': [],
            'codelists': defaultdict(dict),  # filename: fields
            'docs': defaultdict(dict),  # filename: language map
            'readme': {},  # language map
            'name': {},  # language map
            'description': {},  # language map
            'standard_compatibility': {},
        }

        self._add_registry_metadata_to_output()
        self._download_version()
        self._add_information_from_download_to_output()

        return self.out

    def _add_registry_metadata_to_output(self):
        for standard_version in STANDARD_COMPATIBILITY_VERSIONS:
            self.out['standard_compatibility'][standard_version] = False

    def _download_version(self):
        version_output_dir = self.output_directory / self.version.id / self.version.version
        version_output_file = self.output_directory / self.version.id / '{}-status.json'.format(self.version.version)

        # Trust that frozen versions of core extensions don't change.
        if version_output_file.is_file() and version_output_dir.is_dir() and self.version.core and self.version.version != 'master':  # noqa
            return

        if version_output_file.is_file():
            version_output_file.unlink()

        if version_output_dir.is_dir():
            shutil.rmtree(version_output_dir)

        version_output_dir.mkdir(parents=True)
        response = requests.get(self.version.download_url, allow_redirects=True)
        response.raise_for_status()
        version_zipfile = zipfile.ZipFile(io.BytesIO(response.content))
        names = version_zipfile.namelist()
        start = len(names[0])
        for name in names[1:]:
            if name[-1:] == '/':
                (version_output_dir / name[start:]).mkdir(parents=True)
            else:
                with (version_output_dir / name[start:]).open('wb') as f:
                    f.write(version_zipfile.read(name))

        # Finally, write status file to indicate a successful download
        out_status = {
            # This is in case in the future we change how downloads work,
            # and need to know if something on disk is from the old or new code.
            'disk_data_layout_version': 1
        }
        with version_output_file.open('w') as f:
            json.dump(out_status, f, indent=4)

    def _add_information_from_download_to_output(self):
        self._add_extension_json()
        self._add_readme()
        self._add_docs()
        self._add_codelists()
        for basename in ('record-package-schema.json', 'release-package-schema.json', 'release-schema.json'):
            self._add_schema(basename)

    def _add_extension_json(self, language='en'):
        version_output_dir = self._get_version_output_dir(language)

        with (version_output_dir / 'extension.json').open() as f:
            extension_json = self._normalize_extension_json(json.load(f), language=language)

            for field in ('name', 'description'):
                self.out[field][language] = extension_json[field][language]

            for c_v in STANDARD_COMPATIBILITY_VERSIONS:
                if c_v in extension_json['compatibility']:
                    self.out['standard_compatibility'][c_v] = True

    def _add_schema(self, basename, language='en'):
        version_output_dir = self._get_version_output_dir(language)

        path = version_output_dir / basename
        if path.is_file():
            with path.open() as f:
                try:
                    self.out[path.stem.replace('-', '_')][language] = json.load(f)
                except json.decoder.JSONDecodeError as e:
                    self.out['errors'].append({
                        'message': 'Error while trying to parse {}: {}'.format(path.name, e.msg),
                    })

    def _add_codelists(self, language='en'):
        version_output_dir = self._get_version_output_dir(language)

        codelists_dir_name = version_output_dir / 'codelists'
        if codelists_dir_name.is_dir():
            paths = [f for f in codelists_dir_name.iterdir() if f.is_file()]
            for path in paths:
                data = self.out['codelists'][path.name]

                if 'items' not in data:
                    data['items'] = {}
                if 'fieldnames' not in data:
                    data['fieldnames'] = OrderedDict()

                with path.open() as f:
                    reader = csv.DictReader(f)

                    # Extract the csv headers from the EN version to use as canonical
                    # keys to reference the codes
                    if language == 'en':
                        for fieldname in reader.fieldnames:
                            if fieldname not in data['fieldnames']:
                                data['fieldnames'][fieldname] = {}
                            data['fieldnames'][fieldname]['en'] = fieldname
                    else:
                        # And assume the translated headers will be in the same order as EN
                        en_fieldnames = list(data['fieldnames'].keys())

                        for index, fieldname in enumerate(reader.fieldnames):
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
                                if code not in data['items']:
                                    data['items'][code] = {}
                                data['items'][code][language] = row

    def _add_docs(self, language='en'):
        version_output_dir = self._get_version_output_dir(language)

        docs_dir_name = version_output_dir / 'docs'
        if docs_dir_name.is_dir():
            for path in docs_dir_name.iterdir():
                if path.is_file():
                    with path.open() as f:
                        self.out['docs'][path.name][language] = f.read()  # noqa

    def _add_readme(self, language='en'):
        version_output_dir = self._get_version_output_dir(language)

        readme_filename = version_output_dir / 'README.md'
        if readme_filename.is_file():
            with readme_filename.open() as f:
                self.out['readme'][language] = f.read()

    def _get_version_output_dir(self, language):
        if language == 'en':
            return self.output_directory / self.version.id / self.version.version
        else:
            return self.output_directory / locale_dir / language / 'TRANSLATIONS' / self.version.id / self.version.version  # noqa

    # This def is a candidate for pushing upstream to extension_registry.py
    def _normalize_extension_json(self, in_extension_json, language='en'):
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
