import shutil
from io import BytesIO
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from zipfile import ZipFile

import requests
from ocdsextensionregistry import ExtensionRegistry

from .base import BaseCommand
from ocdsextensionsdatacollector import EXTENSIONS_DATA, EXTENSION_VERSIONS_DATA
from ocdsextensionsdatacollector.exceptions import CommandError


class Command(BaseCommand):
    name = 'download'
    help = 'downloads versions of extensions to a local directory'

    def add_arguments(self):
        self.add_argument('output_directory',
                          help='the directory in which to write the output')
        self.add_argument('versions', nargs='*',
                          help="the versions of extensions to download (e.g. 'bids' or 'lots==master')")
        self.add_argument('--overwrite', choices=['any', 'none', 'live'],
                          help='overwrite any downloaded versions (any), no downloaded versions (none), or only live '
                               'versions (live) like the master branch')
        self.add_argument('--extensions-url', default=EXTENSIONS_DATA,
                          help="the URL of the registry's extensions.csv")
        self.add_argument('--extension-versions-url', default=EXTENSION_VERSIONS_DATA,
                          help="the URL of the registry's extension_versions.csv")

    def handle(self):
        registry = ExtensionRegistry(self.args.extension_versions_url, self.args.extensions_url)

        output_directory = Path(self.args.output_directory)

        versions = defaultdict(list)
        for value in self.args.versions:
            if '==' in value:
                extension, version = value.split('==', 1)
                versions[extension].append(version)
            elif '=' in value:
                # Help users with a common error.
                raise CommandError("Couldn't parse '{}'. Use '==' not '='.".format(value))
            else:
                versions[value]

        for count, version in enumerate(registry):
            if versions and version.id not in versions or versions[version.id] and version.version not in versions[version.id]:
                continue

            version_directory = output_directory / version.id / version.version

            if version_directory.is_dir():
                if self.args.overwrite == 'any' or self.args.overwrite == 'live' and not version.date:
                    shutil.rmtree(version_directory)
                elif self.args.overwrite == 'none' or self.args.overwrite == 'live' and version.date:
                    continue

            try:
                version_directory.mkdir(parents=True)

                # See the `files` method of `ExtensionVersion` for similar code.
                response = requests.get(version.download_url, allow_redirects=True)
                response.raise_for_status()
                with closing(ZipFile(BytesIO(response.content))) as zipfile:
                    infos = zipfile.infolist()
                    start = len(infos[0].filename)
                    for info in infos:
                        if info.filename[-1] != '/' and info.filename[start:] != '.travis.yml':
                            info.filename = info.filename[start:]
                            zipfile.extract(info, version_directory)
            except FileExistsError as e:
                raise CommandError('File {} already exists! Set the --overwrite option.'
                                   .format(e.filename))
