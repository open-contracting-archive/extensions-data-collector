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

## Disk space

The disk space used is the directory "output_dir" in the code folder.

This can be changed by passing the output_directory option to the Runner class or passing the 
--outputdir argument to cli.py.

    python cli.py --outputdir CUSTOMout --sample

## Output

The important output is a data JSON file called "data.json". This will be on disk in the directory specfied after running.

This is used by websites like https://github.com/open-contracting/extension-explorer
