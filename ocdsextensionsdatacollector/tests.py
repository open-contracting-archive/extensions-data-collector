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
