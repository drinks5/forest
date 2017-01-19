
import asyncio
import httptools
from httptools import HttpRequestParser
from datetime import datetime

from .request import Request
from .exceptions import *
from .utils import log
from .response import text


class CIMultiDict(dict):
    pass


class HttpProtocolMixin:
    def __init__(self, *, loop, router, signal):
        self.loop = loop
        self.parser = HttpRequestParser(self)
        self.router = router
        self.signal = signal
        self.connections = set()
        self.request_timeout = 0
        self.url = b''
        self.headers = []
        self._last_request_time = 0
        self._request_handler_task=None
        self._total_request_size = 0
        self.request_max_size = 65535


    def connection_made(self, transport):
        self.connections.add(self)
        # self._timeout_handler = self.loop.call_later(
        #     self.request_timeout, self.connection_timeout)
        self.transport = transport
        self._last_request_time = self.update_time

    def connection_lost(self, exc):
        self.connections.discard(self)
        # self._timeout_handler.cancel()
        self.cleanup()

    def connection_timeout(self):
        # Check if
        time_elapsed = self.update_time - self._last_request_time
        if time_elapsed < self.request_timeout:
            time_left = self.request_timeout - time_elapsed
            self._timeout_handler = \
                self.loop.call_later(time_left, self.connection_timeout)
        else:
            if self._request_handler_task:
                self._request_handler_task.cancel()
            exception = RequestTimeout('Request Timeout')
            self.write_error(exception)

    def data_received(self, data):
        # Check for the request itself getting too large and exceeding
        # memory limits
        self._total_request_size += len(data)
        if self._total_request_size > self.request_max_size:
            exception = PayloadTooLarge('Payload Too Large')
            self.write_error(exception)

        # Create parser if this is the first time we're receiving data
        if self.parser is None:
            assert self.request is None
            self.headers = []
            self.parser = HttpRequestParser(self)

        try:
            self.parser.feed_data(data)
        except HttpParserError:
            exception = InvalidUsage('Bad Request')
            self.write_error(exception)

    def on_url(self, url):
        self.url = url

    def on_header(self, name, value):
        if name == b'Content-Length' and int(value) > self.request_max_size:
            exception = PayloadTooLarge('Payload Too Large')
            self.write_error(exception)

        self.headers.append((name.decode(), value.decode('utf-8')))

    def on_headers_complete(self):
        remote_addr = self.transport.get_extra_info('peername')
        if remote_addr:
            self.headers.append(('Remote-Addr', '%s:%s' % remote_addr))

        self.request = Request(
            url_bytes=self.url,
            headers=CIMultiDict(self.headers),
            version=self.parser.get_http_version(),
            method=self.parser.get_method().decode()
        )

    def on_body(self, body):
        if self.request.body:
            self.request.body += body
        else:
            self.request.body = body

    def on_message_complete(self):
        self._request_handler_task = self.loop.create_task(
                self.router.handler(self.request, self.response_writer))

    # -------------------------------------------- #
    # Responding
    # -------------------------------------------- #

    def response_writer(self, response):
        try:
            keep_alive = self.parser.should_keep_alive() and not self.signal.stopped
            self.transport.write(
                response.output(
                    self.request.version, keep_alive, self.request_timeout))
            if not keep_alive:
                self.transport.close()
            else:
                # Record that we received data
                self._last_request_time = self.update_time
                self.cleanup()
        except Exception:
            from traceback import format_exc
            e = format_exc()
            self.bail_out(
                "Writing response failed, connection closed {}".format(e))

    def write_error(self, exception):
        try:
            response = text(str(exception))

            version = self.request.version if self.request else '1.1'
            self.transport.write(response.output(version))
            self.transport.close()
        except Exception as e:
            self.bail_out(
                "Writing error failed, connection closed {}".format(e))

    def bail_out(self, message):
        exception = ServerError(message)
        self.write_error(exception)
        log.error(message)

    def cleanup(self):
        self.parser = None
        self.request = None
        self.url = None
        self.headers = None
        self._request_handler_task = None
        self._total_request_size = 0

    def close_if_idle(self):
        """
        Close the connection if a request is not being sent or received
        :return: boolean - True if closed, false if staying open
        """
        if not self.parser:
            self.transport.close()
            return True
        return False

class HttpProtocol(HttpProtocolMixin, asyncio.Protocol):
    @property
    def update_time(self):
        return datetime.now().timestamp()
