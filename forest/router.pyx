import re
from functools import lru_cache
from traceback import format_exc
from .response import text, exception
from .request cimport Request


cdef class RouteMatch:
    def __cinit__(self):
        self.handler = None
        self.vars = tuple()


cdef class Router:
    def __cinit__(self):
        self.parent = None
        self.routes = list()
        self.strictSlash = False

    def register(self, str path, handler):
        route = Route(self, handler).path(path)
        self.routes.append(route)
        return route

    @lru_cache(maxsize=5)
    def match(self, Request request, RouteMatch match):
        for route in self.routes:
            if route.match(request, match):
                return True
        return False

    async def handler(self, Request request, response_writer):
        match = RouteMatch()
        if self.match(request, match):
            handler = match.handler
        if not match.handler:
            return response_writer(exception(404))
        try:
            response = await handler(request, *match.vars)
        except:
            info = format_exc()
            response = text(info)
        return response_writer(response)

    def getRegexpGroup(self):
        if self.parent:
            return self.parent.getRegexpGroup()
        return None

    def reset(self):
        from importlib import import_module

        def reimport(func):
            module = import_module(func.__module__)
            return getattr(module, func.__name__)
        for route in self.routes:
            route.handler = reimport(route.handler)
        self.match.cache_clear()


cdef class RouteRegexpGroup:
    def __cinit__(self, host=None, path=None, queries=None):
        self.host = host
        self.path = path
        self.queries = queries


cdef class Route:
    def __cinit__(self, Router router, object handler):
        self.parent = router
        self.strictSlash = router.strictSlash
        self.matchers = []
        self.handler = handler
        self.regexp = None

    def path(self, tpl):
        self.addRegexpMatcher(tpl)
        return self

    def addRegexpMatcher(self, str tpl):
        self.regexp = self.getRegexpGroup()
        rr = self.get_regexp(
                tpl,
                matchPrefix=False,
                strictSlash=False)
        self.matchers.append(rr)

    def getRegexpGroup(self) -> RouteRegexpGroup:
        if self.regexp:
            return self.regexp
        if not self.parent:
            self.parent = Router()
        regexp = self.parent.getRegexpGroup()
        if not regexp:
            self.regexp = RouteRegexpGroup()
        else:
            self.regexp = RouteRegexpGroup(
                host=regexp.host, path=regexp.path, queries=regexp.queries)
        return self.regexp

    def get_regexp(self, tpl, matchPrefix=False, strictSlash=False):

        pattern = r'\{(.*?)\}'
        reverse = ''

        def repl(matchobj):
            parts = matchobj.group(0)[1:-1].split(':', 1)
            name = parts[0]
            patt = len(parts) == 2 and parts[1] or '[^/]+'
            return "(?P<%s>%s)" % (name, patt)
        pattern = re.sub(pattern, repl, tpl)
        if matchPrefix:
            strictSlash = False
        reg = re.compile(pattern)
        return RouteRegexp(tpl, reg, reverse, strictSlash)

    def match(self, Request request, RouteMatch match):
        for m in self.matchers:
            if not m.match(request, match):
                return False
        if not match.handler:
            match.handler = self.handler
        if not match.vars:
            vars = m.pattern.findall(request.path)
            if vars:
                match.vars = vars[0]
        return True


class RouteRegexp:
    def __init__(self, str template, object regexp, object reverse, bint strictSlash=False):
        self.template = template
        self.pattern = regexp
        self.reverse = reverse
        self.strictSlash = strictSlash

    def match(self, Request request, RouteMatch match):
        path = request.path
        return self.pattern.match(path)
