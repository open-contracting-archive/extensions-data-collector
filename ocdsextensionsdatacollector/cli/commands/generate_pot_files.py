import logging
import subprocess
from contextlib import closing
from glob import glob
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import requests
from babel.messages.catalog import Catalog
from babel.messages.extract import extract, pathmatch
from babel.messages.pofile import write_po
from ocds_babel.extract import extract_codelist, extract_schema, extract_extension_metadata
from recommonmark.parser import CommonMarkParser
from sphinx.application import Sphinx
from sphinx.util.osutil import cd

from .base import BaseCommand
from ocdsextensionsdatacollector import EXTENSIONS_DATA, EXTENSION_VERSIONS_DATA

logger = logging.getLogger('ocdsextensionsdatacollector')


class Command(BaseCommand):
    name = 'generate-pot-files'
    help = 'generates POT files (message catalogs) for versions of extensions'

    def add_arguments(self):
        self.add_argument('locale_directory',
                          help='the directory in which to write the output')
        self.add_argument('versions', nargs='*',
                          help="the versions of extensions to process (e.g. 'bids' or 'lots==master')")
        self.add_argument('-v', '--verbose', action='store_true',
                          help='print verbose output')
        self.add_argument('--extensions-url', default=EXTENSIONS_DATA,
                          help="the URL of the registry's extensions.csv")
        self.add_argument('--extension-versions-url', default=EXTENSION_VERSIONS_DATA,
                          help="the URL of the registry's extension_versions.csv")

    def handle(self):
        locale_directory = Path(self.args.locale_directory)

        # We simulate pybabel and sphinx-build commands. Variable names are chosen to match upstream code.

        # For sphinx-build, the code path is:
        #
        # * bin/sphinx-build calls main() in sphinx, which calls build_main(), which calls main() in sphinx.cmdline
        # * main() calls Sphinx(…).build(…) in sphinx.application

        # sphinx-build -E -q …
        kwargs = {
            'confoverrides': {
                'master_doc': 'README',
                'source_suffix': '.md',
                'source_parsers': {
                    '.md': CommonMarkParser,
                },
            },
            'freshenv': True,
            'parallel': 1,
        }
        if not self.args.verbose:
            kwargs.update(status=None)

        # For pybabel, the code path is:
        #
        # * bin/pybabel calls main() in babel.messages.frontend
        # * main() calls CommandLineInterface().run(sys.argv)
        # * CommandLineInterface() calls extract_messages(), which:
        #   1. Reads the input path and method map from command-line options
        #   2. Instantiates a catalog
        #   3. Calls extract_from_dir() in babel.messages.extract to extract messages
        #   4. extract_from_dir() calls check_and_call_extract_file() to find the method in the method map
        #   5. check_and_call_extract_file() calls extract_from_file() to open a file for extraction
        #   6. extract_from_file() calls extract() to extract messages
        #   7. Adds the messages to the catalog
        #   8. Writes a POT file

        # 1. Reads the input path and method map from command-line options
        arguments = [
            # pybabel extract -F babel_ocds_codelist.cfg . -o $(POT_DIR)/$(DOMAIN_PREFIX)codelists.pot
            ('codelists.pot', [
                ('codelists/*.csv', extract_codelist),
            ]),
            # pybabel extract -F babel_ocds_schema.cfg . -o $(POT_DIR)/$(DOMAIN_PREFIX)schema.pot
            ('schema.pot', [
                ('*-schema.json', extract_schema),
                ('extension.json', extract_extension_metadata),
            ]),
        ]

        for version in self.versions():
            if not version.download_url:
                logger.warning('No Download URL for {}=={}'.format(version.id, version.version))

            outdir = locale_directory / version.id / version.version

            outdir.mkdir(parents=True, exist_ok=True)

            # See the `files` method of `ExtensionVersion` for similar code.
            response = requests.get(version.download_url, allow_redirects=True)
            response.raise_for_status()
            with closing(ZipFile(BytesIO(response.content))) as zipfile:
                names = zipfile.namelist()
                start = len(names[0])

                for output_file, method_map in arguments:
                    # 2. Instantiates a catalog
                    catalog = Catalog()

                    # 3. Calls extract_from_dir() in babel.messages.extract to extract messages
                    for name in names[1:]:
                        filename = name[start:]

                        # 4. extract_from_dir() calls check_and_call_extract_file()
                        for pattern, method in method_map:
                            if not pathmatch(pattern, filename):
                                continue

                            # 5. check_and_call_extract_file() calls extract_from_file()
                            with zipfile.open(name) as fileobj:
                                # 6. extract_from_file() calls extract() to extract messages
                                for lineno, message, comments, context in extract(method, fileobj):
                                    # 7. Adds the messages to the catalog
                                    catalog.add(message, None, [(filename, lineno)],
                                                auto_comments=comments, context=context)

                            break

                    # 8. Writes a POT file
                    if catalog:
                        with open(outdir / output_file, 'wb') as outfile:
                            write_po(outfile, catalog)

                with TemporaryDirectory() as srcdir:
                    for info in zipfile.infolist()[1:]:
                        filename = info.filename[start:]
                        if filename[-1] != '/' and filename.startswith('docs/') or filename == 'README.md':
                            info.filename = filename
                            zipfile.extract(info, srcdir)

                    # sphinx-build -b gettext $(DOCS_DIR) $(POT_DIR)
                    with cd(srcdir):
                        app = Sphinx('.', None, '.', '.', 'gettext', **kwargs)
                        app.build(True)

                        # https://stackoverflow.com/questions/15408348
                        content = subprocess.run(['msgcat', *glob('*.pot')], check=True, stdout=subprocess.PIPE).stdout

                with open(outdir / 'docs.pot', 'wb') as f:
                    f.write(content)
