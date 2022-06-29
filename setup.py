from setuptools import (
    find_packages,
    setup
)

INSTALL_REQUIRES = (
    'requests',
    'cached_property',
    'bs4',
    'nltk',
    'pdftotext',
    'transformers',
    'unidecode'
)

setup(
    name='oireachtas-data',
    version='0.1.0',
    python_requires='>=3.6',
    description='Oireachtas debate data',
    long_description='Oireachtas debate data',
    author='Robert Lucey',
    url='https://github.com/RobertLucey/oireachtas-data',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=INSTALL_REQUIRES,
    entry_points={
        'console_scripts': [
            'load_debates = oireachtas_data.bin.load_debates:main',
            'pull_debates = oireachtas_data.bin.pull_debates:main',
        ]
    }
)
