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
            'name': {
                'en': self.version.metadata['name']['en'],
            },
            'description': {
                'en': self.version.metadata['description']['en'],
            },
            'compatibility': self.version.metadata['compatibility'],
            'schemas': OrderedDict(),
            'codelists': OrderedDict(),
            'docs': OrderedDict(),
            'readme': {
                'en': self.version.remote('README.md'),
            },
        }

        for name in ('record-package-schema.json', 'release-package-schema.json', 'release-schema.json'):
            if name in self.version.schemas:
                self.out['schemas'][name] = {
                    'en': self.version.schemas[name],
                }
            else:
                self.out['schemas'][name] = {}

        for name in sorted(self.version.codelists):
            self.out['codelists'][name] = {
                'fieldnames': OrderedDict(),
                'rows': {},
            }

            codelist = self.version.codelists[name]
            for fieldname in codelist.fieldnames:
                self.out['codelists'][name]['fieldnames'][fieldname] = {
                    'en': fieldname,
                }
            for row in codelist.rows:
                self.out['codelists'][name]['rows'][row['Code']] = {
                    'en': OrderedDict(row),
                }

        for name, text in self.version.docs.items():
            self.out['docs'][name] = {
                'en': text,
            }

        return self.out
