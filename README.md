# OCDS Extensions Data Collector

This takes data from the OCDS Extension Registry and the extensions themselves.

It produces as output a folder with a copy of each version of each extension, and one big "data.json" file containing all data for the extensions.

This python package will be reused by other code, such as the new extensions website.


## Requirements

  *  The Python packages described as normal in requirements.txt
  *  Some disk space to write files to
  *  A Transifex API key with write access to the ocds-extensions project.

## To Run

To run:

    ocdsextensionsdatacollector output_dir/

For testing and development, you can limit data collection to a few extensions:

    ocdsextensionsdatacollector --limit 5

## Disk space

The disk space used is the directory "output_dir" in the code folder.

This can be changed by changing the `output_directory` argument to the `Runner` class or by passing a different `output-dir` argument on the command-line:

    ocdsextensionsdatacollector another_directory/

## Output

The important output is a data JSON file called "data.json". This will be on disk in the directory specfied after running.

This is used by websites like https://github.com/open-contracting/extension-explorer
