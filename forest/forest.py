from functools import partial, wraps

import uvloop
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
        self.loop = uvloop.new_event_loop()

    def route(self, path):
        def handler(_handler):
            self.router.register(path, _handler)

            @wraps(_handler)
            def inner(*args, **kwargs):
                return _handler(*args, **kwargs)

            return inner

        return handler

    def run(self):
        loop = self.loop
        signal = Signal()
        server = partial(
            HttpProtocol, loop=loop, router=self.router, signal=signal)
        host = '127.0.0.1'
        port = 8000
        options = {'reuse_port': False, 'sock': None, 'backlog': 100}

        server_coroutine = loop.create_server(server, host, port, **options)

        try:
            server = loop.run_until_complete(server_coroutine)
        except Exception as e:
            print(e)
        try:
            loop.run_forever()
        except KeyboardInterrupt as e:
            pass
        except Exception as e:
            print(e)
        finally:
            server.close()
            loop.run_until_complete(server.wait_closed())
            loop.close()
