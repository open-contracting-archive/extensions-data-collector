import shutil
from io import BytesIO
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
    help = 'downloads extensions to a local directory'

    def add_arguments(self):
        self.add_argument('output_directory',
                          help='the directory in which to write the output')
        self.add_argument('--clobber', dest='clobber', action='store_const', const=True,
                          help='overwrite repeated downloads')
        self.add_argument('--no-clobber', dest='clobber', action='store_const', const=False,
                          help='skip repeated downloads')
        self.add_argument('--limit', type=int,
                          help='download only this many extensions')
        self.add_argument('--extensions-url', default=EXTENSIONS_DATA,
                          help="the URL of the registry's extensions.csv")
        self.add_argument('--extension-versions-url', default=EXTENSION_VERSIONS_DATA,
                          help="the URL of the registry's extension_versions.csv")

    def handle(self):
        registry = ExtensionRegistry(self.args.extension_versions_url, self.args.extensions_url)
        output_directory = Path(self.args.output_directory)

        for count, version in enumerate(registry):
            if self.args.limit and count >= self.args.limit:
                break

            version_directory = output_directory / version.id / version.version

            if version_directory.is_dir():
                if self.args.clobber:
                    shutil.rmtree(version_directory)
                elif self.args.clobber is False:
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
                raise CommandError('File {} already exists! Try --clobber to overwrite or --no-clobber to skip.'
                                   .format(e.filename))
