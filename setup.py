#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')
version = open('.VERSION').read()

# get the requirements from requirements.txt file
requirements_file = [line.strip() for line in open('requirements.txt').readlines()
                     if line.strip() and not line.startswith('#')]
requirements = requirements_file

setup(
    name='footylib',
    version=version,
    description='''Get season matches for Footy.eu''',
    long_description=readme + '\n\n' + history,
    author='Oriol Fabregas',
    author_email='fabregas.oriol@gmail.com',
    url='https://github.com/wefner/footy',
    packages=[
        'footylib',
    ],
    package_dir={'footylib':
                 'footylib'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache-2.0",
    zip_safe=False,
    keywords='footylib',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
    ],
    data_files=[
        ('', [
            '.VERSION',
            'LICENSE',
            'AUTHORS.rst',
            'CONTRIBUTING.rst',
            'HISTORY.rst',
            'README.rst',
            'USAGE.rst',
        ]),
    ]
)
