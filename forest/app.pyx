from functools import partial

import asyncio

cimport protocol
from .protocol import HttpProtocol
from .handler import Handler
from .routers import Router


class Signal:
    stopped = False


def handler(request):
    return request


class Forest(object):
    default_config = {'DEBUG': True}

    def __init__(self):
        self.request_middleware = []
        self.response_middleware = []

    def route(self, uri, base=None):
        def handler(_handler):
            Router.add(handler, uri, base)
            return _handler
        return handler

    def run(self):

        loop = asyncio.new_event_loop()
        loop.set_debug(True)

        asyncio.set_event_loop(loop)

        signal = Signal()
        server = partial(
            HttpProtocol,
            loop=loop,
            handler=Handler(),
            signal=signal)
        host = '127.0.0.1'
        port = 8000
        options = {'reuse_port': False, 'sock': None, 'backlog': 100}

        server_coroutine = loop.create_server(
            server, host, port, **options)

        try:
            loop.run_until_complete(server_coroutine)
        except Exception as e:
            print(e)
        try:
            loop.run_forever()
        except Exception as e:
            print(e)
