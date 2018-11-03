import json
import sys
from collections import OrderedDict

from .base import BaseCommand
from ocdsextensionsdatacollector import EXTENSIONS_DATA, EXTENSION_VERSIONS_DATA
from ocdsextensionsdatacollector.exceptions import CommandError


class Command(BaseCommand):
    name = 'generate-data-file'
    help = 'generates a data file in JSON format with all the information about versions of extensions'

    def add_arguments(self):
        self.add_argument('versions', nargs='*',
                          help="the versions of extensions to process (e.g. 'bids' or 'lots==master')")
        self.add_argument('--extensions-url', help="the URL of the registry's extensions.csv",
                          default=EXTENSIONS_DATA)
        self.add_argument('--extension-versions-url', help="the URL of the registry's extension_versions.csv",
                          default=EXTENSION_VERSIONS_DATA)

    def handle(self):
        data = OrderedDict()

        for version in self.versions():
            # Add the extension's data.
            if version.id not in data:
                data[version.id] = OrderedDict([
                    ('id', version.id),
                    ('category', version.category),
                    ('core', version.core),
                    ('name', OrderedDict()),
                    ('description', OrderedDict()),
                    ('latest_version', None),
                    ('versions', OrderedDict()),
                ])

            # Add the version's metadata.
            version_data = OrderedDict([
                ('id', version.id),
                ('date', version.date),
                ('version', version.version),
                ('base_url', version.base_url),
                ('download_url', version.download_url),
                ('metadata', version.metadata),
                ('schemas', OrderedDict()),
                ('codelists', OrderedDict()),
                ('docs', OrderedDict()),
                ('readme', OrderedDict({
                    'en': version.remote('README.md'),
                })),
            ])

            # Add the version's schema.
            for name in ('record-package-schema.json', 'release-package-schema.json', 'release-schema.json'):
                if name in version.schemas:
                    version_data['schemas'][name] = OrderedDict({
                        'en': version.schemas[name],
                    })
                else:
                    version_data['schemas'][name] = {}

            # Add the version's codelists.
            for name in sorted(version.codelists):
                version_data['codelists'][name] = OrderedDict([
                    ('fieldnames', OrderedDict()),
                    ('rows', OrderedDict()),
                ])

                codelist = version.codelists[name]
                for fieldname in codelist.fieldnames:
                    version_data['codelists'][name]['fieldnames'][fieldname] = OrderedDict({
                        'en': fieldname,
                    })
                for row in codelist.rows:
                    version_data['codelists'][name]['rows'][row['Code']] = OrderedDict({
                        'en': OrderedDict(row),
                    })

            # Add the version's documentation.
            for name in sorted(version.docs):
                version_data['docs'][name] = OrderedDict({
                    'en': version.docs[name],
                })

            data[version.id]['versions'][version.version] = version_data

        for _id in data:
            # Determine the latest version.
            versions = data[_id]['versions']
            if 'master' in versions:
                latest_version = 'master'
            else:
                dated = list(filter(lambda item: item[1]['date'], versions.items()))
                if dated:
                    latest_version = sorted(dated, key=lambda item: item[1]['date'])[-1][0]
                else:
                    raise CommandError("Couldn't determine latest version of {}".format(_id))

            # Apply the latest version.
            data[_id]['latest_version'] = latest_version
            for field in ('name', 'description'):
                data[_id][field] = data[_id]['versions'][latest_version]['metadata'][field]

        json.dump(data, sys.stdout, ensure_ascii=False, indent=2, separators=(',', ': '))
