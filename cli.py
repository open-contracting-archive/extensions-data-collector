#!/usr/bin/env python
import argparse
import ocdsextensionsdatacollector.runner


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", help="Run sample only", action="store_true")
    parser.add_argument("--outputdir", help="Output Directory. Will be created if not exist.")

    args = parser.parse_args()

    runner = ocdsextensionsdatacollector.runner.Runner(sample=args.sample, output_directory=args.outputdir)

    runner.run()


if __name__ == '__main__':
    main()
