import sys
from io import StringIO
from unittest.mock import patch

from ocdsextensionsdatacollector.cli.__main__ import main
from tests import read

args = ['ocdsextensionsdatacollector', 'generate-data-file']


def test_command(monkeypatch, tmpdir):
    with patch('sys.stdout', new_callable=StringIO) as actual:
        monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), 'location==v1.1.3'])
        main()

    assert actual.getvalue() == read('location-v1.1.3.json')
