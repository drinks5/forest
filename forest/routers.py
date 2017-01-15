from collections import namedtuple
from urllib.parse import urlparse

from .utils import log
Route = namedtuple('Route', ('handler', 'uri', 'base'))


class Router:

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

    # @classmethod
    # def from_base(cls, uri, base):
    #     if not uri:
    #         raise RouterError('no base for uri:%s' % uri)
    #     if not gg
