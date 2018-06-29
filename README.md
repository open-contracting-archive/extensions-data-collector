# OCDS Extensions Data Collector

This takes data from the OCDS Extension Registry and the extensions themselves.

It produces as output a folder with a copy of each version of each extension, and one big "data.json" file containing all data for the extensions.

This python package will be reused by other code, such as the new extensions website.


## Requirements

  *  The Python packages described as normal in requirements.txt
  *  Some disk space to write files to

## To Run

To run:

    python cli.py

You can also just run a sample:

    python cli.py --sample
