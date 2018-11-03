OCDS Extensions Data Collector
==============================

|PyPI version| |Build Status| |Dependency Status| |Coverage Status|

A suite of command-line tools for working with the OCDS extension registry, including: downloading any versions of extensions; generating POT files (message catalogs) from extension files, as part of a translation worlflow; generating a data file in JSON format, that provides all the information about versions of extensions.

To install::

    pip install ocdsextensionsdatacollector

To see all commands available, run::

    ocdsextensionsdatacollector --help

Commands
--------

download
~~~~~~~~

Downloads versions of extensions to a local directory.

To download all versions of all extensions::

    ocdsextensionsdatacollector download outputdir

To download all versions of specific extensions::

    ocdsextensionsdatacollector download outputdir lots bids

To download specific versions::

    ocdsextensionsdatacollector download outputdir bids==v1.1.3

You can mix and match specifying extensions and versions::

    ocdsextensionsdatacollector download outputdir lots bids==v1.1.3

If you've already downloaded versions of extensions, you will need to specify how to handle repeated downloads using the ``--overwrite`` option.

* ``--overwrite any`` overwrite any downloaded versions
* ``--overwrite none`` overwrite no downloaded versions
* ``--overwrite live`` overwrite only live versions (like the master branch of an extension)

Without the output directory, the extension files are organized like `{extension}/{version}/{files}`, for example: ``lots/v1.1.3/README.md``.

generate-pot-files
~~~~~~~~~~~~~~~~~~

Generates POT files (message catalogs) for versions of extensions, for example::

    ocdsextensionsdatacollector generate-pot-files build/locale

You can specify versions and extensions like with the ``download`` command.

To see Sphinx's standard output, use the ``--verbose`` option.

Without the output directory, the POT files are organized like `{extension}/{version}/{files}`, for example: ``lots/v1.1.3/docs.pot``.

generate-data-file
~~~~~~~~~~~~~~~~~~

Generates a data file in JSON format with all the information about versions of extensions, for example::

    ocdsextensionsdatacollector generate-data-file > data.json

You can specify versions and extensions like with the ``download`` command.

The data file is organized as below. To keep it short, the sample shows only one version of one extension, and only one row of one codelist, and it truncates the Markdown content of documentation files and the parsed content of schema files.

.. code:: json

    {
      "risk_allocation": {
        "id": "risk_allocation",
        "category": "ppp",
        "core": false,
        "name": {
          "en": "Risk Allocation"
        },
        "description": {
          "en": "Draft risk allocation extension for ppp extension"
        },
        "latest_version": "master",
        "versions": {
          "master": {
            "id": "risk_allocation",
            "date": "",
            "version": "master",
            "base_url": "https://raw.githubusercontent.com/open-contracting/ocds-riskAllocation-extension/master/",
            "download_url": "https://github.com/open-contracting/ocds-riskAllocation-extension/archive/master.zip",
            "metadata": {
              "name": {
                "en": "Risk Allocation"
              },
              "description": {
                "en": "Draft risk allocation extension for ppp extension"
              },
              "documentationUrl": {
                "en": "https://github.com/open-contracting/ocds-riskAllocation-extension"
              },
              "compatibility": [
                "1.1"
              ],
              "codelists": [
                "riskAllocation.csv",
                "riskCategory.csv"
              ],
              "schemas": [
                "release-schema.json"
              ]
            },
            "schemas": {
              "record-package-schema.json": {},
              "release-package-schema.json": {},
              "release-schema.json": {
                "en": {
                  "definitions": {
                    …
                  }
                }
              }
            },
            "codelists": {
              "riskAllocation.csv": {
                "fieldnames": {
                  "Code": {
                    "en": "Code"
                  },
                  "Title": {
                    "en": "Title"
                  },
                  "Description": {
                    "en": "Description"
                  }
                },
                "rows": {
                  "publicAuthority": {
                    "en": {
                      "Code": "publicAuthority",
                      "Title": "Public authority",
                      "Description": "The risk is wholly or mostly retained by the public authority"
                    }
                  },
                  …
                }
              },
              …
            },
            "docs": {
              "index.md": {
                "en": "# Risk Allocation Extension\n\nThe risk allocation extension …"
              }
            },
            "readme": {
              "en": "# Risk allocation\n\nThe [framework for disclosure in PPPs](http://pubdocs.worldbank.org/en/773541448296707678/Disclosure-in-PPPs-Framework.pdf) …"
            }
          },
          …
        }
      },
      …
    }


Translation workflow
--------------------

If you haven't already, install ``sphinx-intl`` and ``transifex-client``, and create a `~/.transifexrc <https://docs.transifex.com/client/client-configuration#%7E/-transifexrc>`__ file (replace ``USERNAME`` and ``PASSWORD``)::

    pip install sphinx-intl<1 transifex-client
    sphinx-intl create-transifexrc --transifex-username USERNAME --transifex-password PASSWORD

Generate POT files::

    ocdsextensionsdatacollector generate-pot-files build/locale

Remove any ``.tx/config`` file::

    rm -f .tx/config

Create a ``.tx/config`` file::

    sphinx-intl create-txconfig

Update the ``.tx/config`` file (replace ``ocds-extensions`` with your Transifex project)::

    sphinx-intl update-txconfig-resources --transifex-project-name ocds-extensions --pot-dir build/locale --locale-dir locale

Push source files to Transifex::

    tx push -s

Once you've translated strings on Transifex, pull translation files from Transifex::

    tx pull -a -f

Copyright (c) 2018 Open Contracting Partnership, released under the BSD license

.. |PyPI version| image:: https://badge.fury.io/py/ocdsextensionsdatacollector.svg
   :target: https://badge.fury.io/py/ocdsextensionsdatacollector
.. |Build Status| image:: https://secure.travis-ci.org/open-contracting/extensions-data-collector.png
   :target: https://travis-ci.org/open-contracting/extensions-data-collector
.. |Dependency Status| image:: https://requires.io/github/open-contracting/extensions-data-collector/requirements.svg
   :target: https://requires.io/github/open-contracting/extensions-data-collector/requirements/
.. |Coverage Status| image:: https://coveralls.io/repos/github/open-contracting/extensions-data-collector/badge.png?branch=master
   :target: https://coveralls.io/github/open-contracting/extensions-data-collector?branch=master
