from functools import partial, wraps

import asyncio

from .protocol import HttpProtocol
from .routers import Router


class Signal:
    stopped = False


class Forest(object):
    default_config = {'DEBUG': True}

    def __init__(self):
        self.request_middleware = []
        self.response_middleware = []
        self.router = Router()

    def route(self, path):
        def handler(_handler):
            route = self.router.register(path, _handler)

            @wraps(_handler)
            def inner(*args, **kwargs):
                args += tuple(route.vars)
                return _handler(*args, **kwargs)

            return inner

        return handler

    def run(self):
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        signal = Signal()
        server = partial(
            HttpProtocol, loop=loop, router=self.router, signal=signal)
        host = '127.0.0.1'
        port = 8000
        options = {'reuse_port': False, 'sock': None, 'backlog': 100}

        server_coroutine = loop.create_server(server, host, port, **options)

        try:
            loop.run_until_complete(server_coroutine)
        except Exception as e:
            print(e)
        try:
            loop.run_forever()
        except Exception as e:
            print(e)
