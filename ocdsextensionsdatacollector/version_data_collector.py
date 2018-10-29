from collections import OrderedDict


class VersionDataCollector:
    def __init__(self, version):
        self.version = version
        self.out = None

    def collect(self):
        self.out = OrderedDict([
            ('date', self.version.date),
            ('base_url', self.version.base_url),
            ('download_url', self.version.download_url),
            ('name', OrderedDict({
                'en': self.version.metadata['name']['en'],
            })),
            ('description', OrderedDict({
                'en': self.version.metadata['description']['en'],
            })),
            ('compatibility', self.version.metadata['compatibility']),
            ('schemas', OrderedDict()),
            ('codelists', OrderedDict()),
            ('docs', OrderedDict()),
            ('readme', OrderedDict({
                'en': self.version.remote('README.md'),
            })),
        ])

        for name in ('record-package-schema.json', 'release-package-schema.json', 'release-schema.json'):
            if name in self.version.schemas:
                self.out['schemas'][name] = OrderedDict({
                    'en': self.version.schemas[name],
                })
            else:
                self.out['schemas'][name] = {}

        for name in sorted(self.version.codelists):
            self.out['codelists'][name] = OrderedDict([
                ('fieldnames', OrderedDict()),
                ('rows', OrderedDict()),
            ])

            codelist = self.version.codelists[name]
            for fieldname in codelist.fieldnames:
                self.out['codelists'][name]['fieldnames'][fieldname] = OrderedDict({
                    'en': fieldname,
                })
            for row in codelist.rows:
                self.out['codelists'][name]['rows'][row['Code']] = OrderedDict({
                    'en': OrderedDict(row),
                })

        for name in sorted(self.version.docs):
            self.out['docs'][name] = OrderedDict({
                'en': self.version.docs[name],
            })

        return self.out
