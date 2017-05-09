# coding: utf-8
import sys
from setuptools import setup, Extension


requirements = [
    'cffi>=0.8.2',
    'wrapt>=1.6.0'
]

if sys.version_info < (3, 4):
    requirements.append('enum34>=0.9.23')


setup(
    name='httpparser',
    version='0.1.0-dev',
    url='https://github.com/DasIch/httpparser',
    author='Daniel Neuhäuser',
    author_email='ich@danielneuhaeuser.de',

    packages=['httpparser'],
    ext_modules=[
        Extension('httpparser._http_parser', ['http-parser-2.7.1/http_parser.c'])
    ],
    include_package_data=True,
    install_requires=requirements
)
