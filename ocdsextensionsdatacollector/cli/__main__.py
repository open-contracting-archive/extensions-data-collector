import argparse

from ocdsextensionsdatacollector.runner import Runner


def main():
    parser = argparse.ArgumentParser(description='OCDS Extensions Data Collector CLI')
    parser.add_argument('output_directory', help='the directory in which to write the output')
    parser.add_argument('--limit', help='limit data collection to this many extensions', type=int)
    parser.add_argument('--tx-api-key', help='your Transifex API key')

    args = parser.parse_args()

    runner = Runner(args.output_directory, limit=args.limit, tx_api_key=args.tx_api_key)
    runner.run()


if __name__ == '__main__':
    main()
