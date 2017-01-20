
import asyncio
from httptools import HttpRequestParser
from multidict import CIMultiDict

from .request import Request
from .exceptions import HttpError
from .utils import log
from .response import text, exception
from .router import Router


cdef class HttpProtocolMixin:
    def __cinit__(self, *, object loop, Router router, object signal):
        self.loop = loop
        self.parser = HttpRequestParser(self)
        self.router = router
        self.signal = signal
        self.connections = set()
        self.request_timeout = 10
        self.url = b''
        self.headers = []
        self._last_request_time = 0
        self._request_handler_task = None
        self._total_request_size = 0
        self.request_max_size = 65535
        self._timeout_handler = None
        self.time = loop.time
        self.request = None

    def connection_made(self, object transport):
        self.connections.add(self)
        self._timeout_handler = self.loop.call_later(
            self.request_timeout, self.connection_timeout)
        self.transport = transport
        self._last_request_time = self.time()

    def connection_lost(self, object exc):
        self.connections.discard(self)
        self._timeout_handler.cancel()
        self.cleanup()

    def connection_timeout(self):
        # Check if
        time_elapsed = self.time() - self._last_request_time
        if time_elapsed >= self.request_timeout:
            if self._request_handler_task:
                self._request_handler_task.cancel()
            exception = HttpError(408)
            self.write_error(exception)

    def data_received(self, bytes data):
        # Check for the request itself getting too large and exceeding
        # memory limits
        self._total_request_size += len(data)
        if self._total_request_size > self.request_max_size:
            exception = HttpError(413)
            self.write_error(exception)
        try:
            self.parser.feed_data(data)
        except Exception:
            exception = HttpError(400)
            self.write_error(exception)

    def on_url(self, bytes url):
        self.url = url

    def on_header(self, bytes name, bytes value):
        if name == b'Content-Length' and int(value) > self.request_max_size:
            exception = HttpError(431)
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

    def on_body(self, bytes body):
        self.request.body += body

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
                self._last_request_time = self.time()
                self.cleanup()
        except Exception:
            from traceback import format_exc
            e = format_exc()
            self.bail_out(
                b"Writing response failed, connection closed %s" % e)

    def write_error(self, object exc):
        try:
            status_code = getattr(exc, 'status_code', None)
            if status_code:
                response = exception(status_code)
            else:
                response = text(str(exception))
            from traceback import format_exc
            e = format_exc()
            print(e)

            version = self.request.version if self.request else '1.1'
            self.transport.write(response.output(version))
            self.transport.close()
        except Exception as e:
            self.bail_out(
                b"Writing error failed, connection closed %s" % e)

    def bail_out(self, bytes message):
        exception = HttpError(500)
        self._write_error(exception)
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
    pass
