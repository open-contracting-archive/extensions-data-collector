import tempfile
import os
import json
import ocdsextensionsdatacollector.runner


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
