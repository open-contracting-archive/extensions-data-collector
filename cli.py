#!/usr/bin/env python
import argparse
import ocdsextensionsdatacollector.runner


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", help="Run sample only", action="store_true")

    args = parser.parse_args()

    runner = ocdsextensionsdatacollector.runner.Runner(sample=args.sample)

    runner.run()


if __name__ == '__main__':
    main()
