import argparse
import importlib
import logging.config
import sys

from ocdsextensionsdatacollector.exceptions import CommandError

logger = logging.getLogger('ocdskit')

COMMAND_MODULES = (
    'ocdsextensionsdatacollector.cli.commands.download',
)


def main():
    parser = argparse.ArgumentParser(description='OCDS Extensions Data Collector CLI')

    subparsers = parser.add_subparsers(dest='subcommand')

    subcommands = {}

    for module in COMMAND_MODULES:
        try:
            command = importlib.import_module(module).Command(subparsers)
            subcommands[command.name] = command
        except ImportError as e:
            logger.error('exception "%s" prevented loading of %s module', e, module)

    args = parser.parse_args()

    if args.subcommand:
        command = subcommands[args.subcommand]
        try:
            command.args = args
            command.handle()
        except CommandError as e:
            logger.critical(e)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
