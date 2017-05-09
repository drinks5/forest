# coding: utf-8
"""
    httpparser._compat
    ~~~~~~~~~~~~~~~~~~

    :copyright: 2014 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import sys


PY2 = sys.version_info[0] == 2


if PY2:
    def implements_to_string(cls):
        cls.__unicode__ = cls.__str__
        del cls.__str__
        cls.__str__ = cls.__bytes__
        del cls.__bytes__
        return cls
else:
    def implements_to_string(cls):
        return cls


def with_metaclass(meta, *bases):
    return meta('NewBase', bases, {})
