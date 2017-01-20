import re
from functools import lru_cache
from .response import text


class RouteMatch:
    def __init__(self):
        self.handler = None
        self.vars = []


async def not_found(request, *args, **kwargs):
    print('not found !!')
    print(str(request))
    return text(request)


class Router:
    parent = None
    routes = []
    strictSlash = False

    def register(self, path: str, handler):
        route = Route(self, handler).path(path)
        self.routes.append(route)
        return route

    @lru_cache(maxsize=5)
    def match(self, request, match: RouteMatch) -> bool:
        for route in self.routes:
            if route.match(request, match):
                return True
        return False

    async def handler(self, request, response_writer):
        match = RouteMatch()
        if self.match(request, match):
            handler = match.handler
        if not match.handler:
            handler = not_found
        try:
            response = await handler(request, *match.vars)
        except Exception as e:
            print(e)
            response = text('error')
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


class RouteRegexpGroup:
    def __init__(self, host=None, path=None, queries=None):
        self.host = host
        self.path = path
        self.queries = queries


class Route:
    def __init__(self, router: Router, handler):
        self.parent = router
        self.strictSlash = router.strictSlash
        self.matchers = []
        self.handler = handler
        self.regexp = None

    def path(self, tpl):
        self.addRegexpMatcher(tpl)
        return self

    def addRegexpMatcher(self, tpl: str):
        self.regexp = self.getRegexpGroup()
        rr = regexp(
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

    def match(self, request, match: RouteMatch) -> bool:
        for m in self.matchers:
            if not m.match(request, match):
                return False
        if not match.handler:
            match.handler = self.handler
        if not match.vars:
            vars = m.regexp.findall(request.path)
            if vars:
                match.vars = vars[0]
        return True


class RouteRegexp:
    def __init__(self, template, regexp, reverse, strictSlash=False):
        self.template = template
        self.regexp = regexp
        self.reverse = reverse
        self.strictSlash = strictSlash

    def match(self, request, match: RouteMatch) -> bool:
        path = request.path
        return self.regexp.match(path)


def regexp(tpl: str,
           matchPrefix: bool=False,
           strictSlash: bool=False) -> RouteRegexp:

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
