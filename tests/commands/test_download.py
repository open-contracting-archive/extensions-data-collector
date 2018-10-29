import os
import sys
from glob import glob
from io import StringIO
from unittest.mock import patch

import pytest

from ocdsextensionsdatacollector.cli.__main__ import main

args = ['ocdsextensionsdatacollector', 'download']


def test_command(monkeypatch, tmpdir):
    with patch('sys.stdout', new_callable=StringIO) as actual:
        monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1'])
        main()

    assert actual.getvalue() == ''

    tree = list(os.walk(tmpdir))

    assert len(tree) == 3
    # extensions
    assert len(tree[0][1]) == 1
    assert len(tree[0][2]) == 0
    # versions
    assert len(tree[1][1]) == 1
    assert len(tree[1][2]) == 0
    # files
    assert 'extension.json' in tree[2][2]


def test_command_repeated(monkeypatch, tmpdir, caplog):
    monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1'])
    main()

    with pytest.raises(SystemExit) as excinfo:
        with patch('sys.stdout', new_callable=StringIO) as actual:
            monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1'])
            main()

    assert actual.getvalue() == ''

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == 'CRITICAL'
    assert caplog.records[0].message.endswith('Try --clobber to overwrite or --no-clobber to skip.')
    assert excinfo.value.code == 1


def test_command_repeated_clobber(monkeypatch, tmpdir):
    pattern = str(tmpdir / '*' / '*' / 'extension.json')

    monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1'])
    main()

    # Remove a file, to test whether its download is repeated.
    os.unlink(glob(pattern)[0])

    with patch('sys.stdout', new_callable=StringIO) as actual:
        monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1', '--clobber'])
        main()

    assert actual.getvalue() == ''

    assert len(glob(pattern)) == 1


def test_command_repeated_no_clobber(monkeypatch, tmpdir):
    pattern = str(tmpdir / '*' / '*' / 'extension.json')

    monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1'])
    main()

    # Remove a file, to test whether its download is repeated.
    os.unlink(glob(pattern)[0])

    with patch('sys.stdout', new_callable=StringIO) as actual:
        monkeypatch.setattr(sys, 'argv', args + [str(tmpdir), '--limit', '1', '--no-clobber'])
        main()

    assert actual.getvalue() == ''

    assert len(glob(pattern)) == 0


def test_command_help(monkeypatch, caplog):
    with pytest.raises(SystemExit) as excinfo:
        with patch('sys.stdout', new_callable=StringIO) as actual:
            monkeypatch.setattr(sys, 'argv', ['ocdsextensionsdatacollector', '--help'])
            main()

    assert actual.getvalue().startswith('usage: ocdsextensionsdatacollector [-h] ')

    assert len(caplog.records) == 0
    assert excinfo.value.code == 0
