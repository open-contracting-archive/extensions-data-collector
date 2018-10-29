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
            'readme': {
                'en': self.version.remote('README.md'),
            },
            'name': {
                'en': self.version.metadata['name']['en'],
            },
            'description': {
                'en': self.version.metadata['description']['en'],
            },
            'standard_compatibility': self.version.metadata['compatibility'],
        }

        for name in ('record-package-schema.json', 'release-package-schema.json', 'release-schema.json'):
            if name in self.version.schemas:
                self.out[name.replace('-', '_').replace('.json', '')] = {
                    'en': self.version.schemas[name],
                }

        for name in sorted(self.version.codelists):
            self.out['codelists'][name] = {
                'items': {},
                'fieldnames': OrderedDict(),
            }

            codelist = self.version.codelists[name]
            for fieldname in codelist.fieldnames:
                self.out['codelists'][name]['fieldnames'][fieldname] = {
                    'en': fieldname,
                }
            for row in codelist.rows:
                self.out['codelists'][name]['items'][row['Code']] = {
                    'en': OrderedDict(row),
                }

        for name, text in self.version.docs.items():
            self.out['docs'][name] = {
                'en': text,
            }

        return self.out
