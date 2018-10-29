import tempfile
import os
import json
import ocdsextensionsdatacollector.runner
import ocdsextensionregistry


def test_write_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = ocdsextensionsdatacollector.runner.Runner(output_directory=tmpdir)
        runner.out = {
            'test_output_to_write': 'is_very_good'
        }
        runner._write_output()

        assert os.path.isfile(os.path.join(tmpdir, 'data.json'))
        with open(os.path.join(tmpdir, 'data.json')) as infile:
            test_out = json.load(infile)

            assert test_out['test_output_to_write'] == 'is_very_good'


def test_add_information_from_download_to_output():
    runner = ocdsextensionsdatacollector.runner.Runner(
        output_directory=os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'tests',
            'test_add_information_from_download_to_output'
        ),
    )
    runner.out = {'extensions': {}}

    extensions_data = """Id,Category,Core
extension_one,Test,true"""

    extension_versions_data = """Id,Date,Version,Base URL,Download URL
extension_one,2017-05-09,master,http://example.com/,http://example.com/"""

    registry = ocdsextensionregistry.ExtensionRegistry(extension_versions_data, extensions_data)

    for version in registry:
        runner._add_registry_metadata_to_output(version)
        runner._add_information_from_download_to_output(version)

    assert runner.out['extensions']['extension_one']['versions']['master']['name']['en'] == \
        'Extension One'
    assert runner.out['extensions']['extension_one']['versions']['master']['description']['en'] == \
        'The First Extension'


def test_add_information_from_latest_version_to_extension():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = ocdsextensionsdatacollector.runner.Runner(output_directory=tmpdir)
        runner.out = {
            'extensions': {
                'extension_one': {
                    'versions': {
                        'master': {
                            "name": {
                                "en": "Extension One"
                            },
                            "description": {
                                "en": "The First Extension"
                            }
                        }
                    }
                }
            }
        }

        assert runner._get_main_version_for_extension('extension_one') == "master"

        runner._add_information_from_version_to_extension(
            'extension_one',
            runner._get_main_version_for_extension('extension_one')
        )

        assert runner.out['extensions']['extension_one']['name']['en'] == \
            'Extension One'
        assert runner.out['extensions']['extension_one']['description']['en'] == \
            'The First Extension'
