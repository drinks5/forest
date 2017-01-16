from collections import namedtuple
from urllib.parse import urlparse
import re

from .utils import log
Route = namedtuple('Route', ('handler', 'uri', 'base'))


class Router(object):

    maps = {}

    @classmethod
    def add(cls, handler, uri, base):
        if not base:
            cls.maps[uri] = Route(handler, uri, base)
            return
        uri = cls.from_base(uri, base)
        cls.maps[uri] = handler

    @classmethod
    def get(cls, request):
        uri = urlparse(request.url).path
        route = cls.maps.get(uri.decode('utf8'))
        log.error('uri:%s, handler:%s, maps:%s', uri, route, cls.maps)

        if not route:
            return

        return route.handler

    def __call__(self, path, name):
        def inner(func):
            return func

        return inner


pattern = re.compile(r'\{(.*?)\}')


def regexp(tpl, matchHost, matchPrefix, matchQuery, strictSlash, useEncodedPath):

    defaultPattern = "[^/]+"
    if matchQuery:
        defaultPattern = "[^?&]*"
    elif matchHost:
        defaultPattern = "[^.]+"
        matchPrefix = False
    # Only match strict slash if not matching
    if matchPrefix or matchHost or matchQuery:
        strictSlash = False
    # Set a flag for strictSlash.

