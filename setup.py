from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

setup(
    name='ocdsextensionsdatacollector',
    version='0.0.1',
    author='Open Contracting Partnership, Open Data Services',
    author_email='data@open-contracting.org',
    url='https://github.com/open-contracting/extensions-data-collector',
    description='Collects data about OCDS extensions into a machine-readable format',
    license='BSD',
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type='text/markdown',
    scripts=['cli.py'],
    install_requires=[
      'ocdsextensionregistry>=0.0.3',
      'polib',
      'python-decouple',
      'requests',
    ],
    extras_require={
        'test': [
            'coveralls',
            'pytest',
            'pytest-cov',
        ],
    },
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.6',
    ],
)
