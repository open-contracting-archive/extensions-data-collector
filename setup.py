#!/usr/bin/env python
import io
import os
from distutils.core import setup


here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

setup(name='ocdsextensionsdatacollector',
      version='0.0.1',
      description='Collect data about Open Contracting Data Standard Extensions ' +
                  'into a machine readable format for re-use',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Open Contracting Partnership, Open Data Services',
      author_email='data@open-contracting.org',
      url='https://open-contracting.org',
      license='BSD',
      packages=[
            'ocdsextensionsdatacollector'
      ],
      scripts=['cli.py']
      )
