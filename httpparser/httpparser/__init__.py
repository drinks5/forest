# coding: utf-8
"""
    httpparser
    ~~~~~~~~~~

    :copyright: 2014 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import sys
from enum import Enum
from contextlib import contextmanager
from collections import namedtuple
from weakref import WeakKeyDictionary

from wrapt import decorator

from httpparser._bindings import ffi, lib
from httpparser._compat import with_metaclass, implements_to_string


#: The httpparser version as string.
__version__ = u'0.1.0-dev'
#: The httpparser version as tuple.
__version_info__ = (0, 1, 0)


def _get_http_parser_version():
    version = lib.http_parser_version()
    major = (version >> 16) & 255
    minor = (version >> 8) & 255
    patch = version & 255
    return major, minor, patch


_CALLBACKS = {
    'on_message_begin': 'http_cb',
    'on_url': 'http_data_cb',
    'on_status': 'http_data_cb',
    'on_header_field': 'http_data_cb',
    'on_header_value': 'http_data_cb',
    'on_headers_complete': 'http_cb',
    'on_body': 'http_data_cb',
    'on_message_complete': 'http_cb'
}


#: The version of the underlying http-parser C library as string.
__http_parser_version__ = u'{}.{}.{}'.format(*_get_http_parser_version())
#: The version of the underlying http-parser C library as tuple.
__http_parser_version_info__ = _get_http_parser_version()


@implements_to_string
class Method(Enum):
    """
    A :class:`enum.Enum` that represents an HTTP method.
    """
    delete = lib.HTTP_DELETE
    get = lib.HTTP_GET
    head = lib.HTTP_HEAD
    post = lib.HTTP_POST
    put = lib.HTTP_PUT
    connect = lib.HTTP_CONNECT
    options = lib.HTTP_OPTIONS
    trace = lib.HTTP_TRACE
    # webdav
    copy = lib.HTTP_COPY
    lock = lib.HTTP_LOCK
    mkcol = lib.HTTP_MKCOL
    move = lib.HTTP_MOVE
    propfind = lib.HTTP_PROPFIND
    proppatch = lib.HTTP_PROPPATCH
    search = lib.HTTP_SEARCH
    unlock = lib.HTTP_UNLOCK
    # subversion
    report = lib.HTTP_REPORT
    mkactivity = lib.HTTP_MKACTIVITY
    checkout = lib.HTTP_CHECKOUT
    merge = lib.HTTP_MERGE
    # upnp
    msearch = lib.HTTP_MSEARCH
    notify = lib.HTTP_NOTIFY
    subscribe = lib.HTTP_SUBSCRIBE
    unsubscribe = lib.HTTP_UNSUBSCRIBE
    # rfc 5789
    patch = lib.HTTP_PATCH
    purge = lib.HTTP_PURGE

    def __bytes__(self):
        return ffi.string(lib.http_method_str(self.value))

    def __str__(self):
        return bytes(self).decode('ascii')

    def __repr__(self):
        return '<{}.{}: {}>'.format(
            self.__class__.__name__, self.name, self
        )


class ParserType(Enum):
    """
    A :class:`enum.Enum` that represents a parser type.
    """
    request = lib.HTTP_REQUEST
    response = lib.HTTP_RESPONSE
    both = lib.HTTP_RESPONSE


class Errno(Enum):
    """
    A :class:`enum.Enum` that represents an :class:`HTTPParser` errno.
    """
    ok = lib.HPE_OK

    # callback related errors
    cb_message_begin = lib.HPE_CB_message_begin
    cb_url = lib.HPE_CB_url
    cb_header_field = lib.HPE_CB_header_field
    cb_header_value = lib.HPE_CB_header_value
    cb_headers_complete = lib.HPE_CB_headers_complete
    cb_body = lib.HPE_CB_body
    cb_message_complete = lib.HPE_CB_message_complete
    cb_status = lib.HPE_CB_status

    # parsing-related errors
    invalid_eof_state = lib.HPE_INVALID_EOF_STATE
    header_overflow = lib.HPE_HEADER_OVERFLOW
    closed_connection = lib.HPE_CLOSED_CONNECTION
    invalid_version = lib.HPE_INVALID_VERSION
    invalid_status = lib.HPE_INVALID_STATUS
    invalid_method = lib.HPE_INVALID_METHOD
    invalid_url = lib.HPE_INVALID_URL
    invalid_host = lib.HPE_INVALID_HOST
    invalid_port = lib.HPE_INVALID_PORT
    invalid_path = lib.HPE_INVALID_PATH
    invalid_query_string = lib.HPE_INVALID_QUERY_STRING
    invalid_fragment = lib.HPE_INVALID_FRAGMENT
    lf_expected = lib.HPE_LF_EXPECTED
    invalid_header_token = lib.HPE_INVALID_HEADER_TOKEN
    invalid_content_length = lib.HPE_INVALID_CONTENT_LENGTH
    invalid_chunk_size = lib.HPE_INVALID_CHUNK_SIZE
    invalid_constant = lib.HPE_INVALID_CONSTANT
    invalid_internal_state = lib.HPE_INVALID_INTERNAL_STATE
    strict = lib.HPE_STRICT
    paused = lib.HPE_PAUSED
    unknown = lib.HPE_UNKNOWN

    @property
    def c_name(self):
        """
        The name used by the underlying the library.
        """
        return ffi.string(lib.http_errno_name(self.value)).decode('ascii')

    @property
    def description(self):
        """
        A description for this error.
        """
        return ffi.string(lib.http_errno_description(self.value)).decode('ascii')


class ConnectionUpgrade(Exception):
    """
    Indicates an upgraded HTTP connection.
    """
    def __init__(self, offset):
        Exception.__init__(self, offset)
        #: Indicates the beginning of the body in the last piece of data on
        #: which the parser was executed.
        self.offset = offset


class HTTPParserError(Exception):
    """
    Represents an error, corresponding to a :class:`Errno` instance.
    """
    def __init__(self, errno, offset):
        super(HTTPParserError, self).__init__(
            '{} ({}): {}'.format(errno.name, errno.c_name, errno.description)
        )
        self.errno = errno
        self.offset = offset


def _call_http_cb(wrapped, instance, args, kwargs, callback_name, allow_failure):
    try:
        result = wrapped(*args, **kwargs)
    except Exception as error:
        wrapped.__func__.last_exception = error
        if allow_failure:
            return 1
        return False
    if isinstance(result, int):
        return result
    elif result is None:
        return 0
    else:
        # cffi callbacks must not fail with an exception. Nevertheless we want
        # to report an exception here, so we raise an exception and immediately
        # catch it to get a traceback pointing to this location and re-raise
        # that exception later.
        try:
            raise TypeError(
                (
                    'expected None or integer from {} callback of {!r}, '
                    'received {!r}'
                ).format(callback_name, instance, result)
            )
        except TypeError as error:
            wrapped.__func__.last_exception = error
        return 1 if allow_failure else 0


class _HTTPParserCallback(object):
    def __init__(self, name, function, allow_failure=True):
        self.name = name
        self.function = function
        self.function._set_callback = self._set_callback
        self.function.last_exception = None
        self.allow_failure = allow_failure
        self.callbacks = WeakKeyDictionary()

    @property
    def function(self):
        return self._function

    @function.setter
    def function(self, new_function):
        self._function = new_function

    def __get__(self, instance, owner):
        return self.function.__get__(instance, owner)

    def __set__(self, instance, value):
        value.__name__ = self.function.__name__
        self.function = value
        self._set_callback(instance)

    def _wrap_in_callback(self, function, instance):
        @decorator
        def safe_callback(wrapped, instance, args, kwargs):
            return _call_http_cb(
                wrapped, instance, (), kwargs, self.name, self.allow_failure
            )
        unbound = function.__get__(None, instance.__class__)
        unbound_callback = safe_callback(unbound)
        bound_callback = unbound_callback.__get__(instance, instance.__class__)
        return ffi.callback('http_cb', bound_callback)

    def _set_callback(self, instance):
        callback = self.callbacks[instance] = self._wrap_in_callback(
            self.function, instance
        )
        setattr(instance._settings, self.name, callback)


class _HTTPParserDataCallback(_HTTPParserCallback):
    def _wrap_in_callback(self, function, instance):
        @decorator
        def safe_callback(wrapped, instance, args, kwargs):
            buffer, data_len = args[1:]
            data = ffi.string(buffer[0:data_len])
            return _call_http_cb(
                wrapped, instance, (data, ), kwargs, self.name,
                self.allow_failure
            )
        unbound = function.__get__(None, instance.__class__)
        unbound_callback = safe_callback(unbound)
        bound_callback = unbound_callback.__get__(instance, instance.__class__)
        return ffi.callback('http_data_cb', bound_callback)


class HTTPParserMeta(type):
    def __init__(self, name, bases, attributes):
        # Unfortunately this is necessary so that the properties are triggered.
        super(HTTPParserMeta, self).__init__(name, bases, attributes)
        for attribute_name, attribute in attributes.items():
            if attribute_name in _CALLBACKS:
                setattr(self, attribute_name, attribute)

    @property
    def on_message_begin(self):
        return self._on_message_begin

    @on_message_begin.setter
    def on_message_begin(self, new_callback):
        self._on_message_begin = _HTTPParserCallback(
            'on_message_begin', new_callback
        )

    @property
    def on_url(self):
        return self._on_url

    @on_url.setter
    def on_url(self, new_callback):
        self._on_url = _HTTPParserDataCallback('on_url', new_callback)

    @property
    def on_status(self):
        return self._on_status

    @on_status.setter
    def on_status(self, new_callback):
        self._on_status = _HTTPParserDataCallback('on_status', new_callback)

    @property
    def on_header_field(self):
        return self._on_header_field

    @on_header_field.setter
    def on_header_field(self, new_callback):
        self._on_header_field = _HTTPParserDataCallback(
            'on_header_field', new_callback
        )

    @property
    def on_header_value(self):
        return self._on_header_value

    @on_header_value.setter
    def on_header_value(self, new_callback):
        self._on_header_value = _HTTPParserDataCallback(
            'on_header_value', new_callback
        )

    @property
    def on_headers_complete(self):
        return self._on_headers_complete

    @on_headers_complete.setter
    def on_headers_complete(self, new_callback):
        self._on_headers_complete = _HTTPParserCallback(
            'on_headers_complete', new_callback, allow_failure=False
        )

    @property
    def on_body(self):
        return self._on_body

    @on_body.setter
    def on_body(self, new_callback):
        self._on_body = _HTTPParserDataCallback('on_body', new_callback)

    @property
    def on_message_complete(self):
        return self._on_message_complete

    @on_message_complete.setter
    def on_message_complete(self, new_callback):
        self._on_message_complete = _HTTPParserCallback(
            'on_message_complete', new_callback
        )


class HTTPParser(with_metaclass(HTTPParserMeta, object)):
    """
    A :class:`HTTPParser` provides an asynchronous per-connection parser. Users
    are expected to subclass this class and implement the `on_*` methods, to
    store and further parse individual headers and the message body.

    When implementing the callbacks keep in mind that they may be called
    multiple times to construct a single value. The entire message url for
    example consists of all strings :meth:`on_url` is called with concatenated
    within a single message. Other callbacks behave similarly.
    """
    def __init__(self, parser_type):
        self._parser = ffi.new('http_parser*')
        lib.http_parser_init(self._parser, ParserType(parser_type).value)
        self._settings = ffi.new('http_parser_settings*')
        for callback_name in _CALLBACKS:
            method = getattr(self, callback_name)
            method._set_callback(self)

    @property
    def http_major(self):
        """
        The HTTP major version.
        """
        return self._parser.http_major

    @property
    def http_minor(self):
        """
        The HTTP minor version.
        """
        return self._parser.http_minor

    @property
    def status_code(self):
        """
        The status code (only for responses).
        """
        return self._parser.status_code

    @property
    def method(self):
        """
        The HTTP method as :class:`Method` attribute.
        """
        return Method(self._parser.method)

    @property
    def http_errno(self):
        """
        The errno value of the parser as :class:`Errno` attribute.
        """
        return Errno(self._parser.http_errno)

    @property
    def upgrade(self):
        """
        `True` if an upgrade header was present and the parser exited because
        of that.
        """
        return self._parser.upgrade == 1

    @property
    def pause(self):
        """
        `True` if the parser is paused. Can be set to `True` or `False`.
        """
        return self.http_errno is Errno.paused

    @pause.setter
    def pause(self, toggle):
        if toggle:
            lib.http_parser_pause(self._parser, 1)
        else:
            lib.http_parser_pause(self._parser, 0)

    def should_keep_alive(self):
        """
        Returns `True` if called in the `on_headers_complete` or
        `on_message_complete` callbacks.
        """
        return bool(lib.http_should_keep_alive(self._parser))

    def body_is_final(self):
        """
        Returns `True`, if this is the final chunk of the body.
        """
        return lib.http_body_is_final(self._parser)

    def execute(self, data):
        """
        Parses the given `data`.

        May raise :exc:`HTTPParserError` or any exception that might be thrown
        by a callback method.

        If an upgrade request was received, the parser will ignore the body of
        the request and raise a :exc:`ConnectionUpgrade` exception. The
        `offset` attribute on the exception will indicate where in the given
        `data` the body begins.
        """
        if not isinstance(data, bytes):
            raise TypeError('expected bytes, received {!r}'.format(data))
        data_len = len(data)
        with self._callback_exception():
            parsed = lib.http_parser_execute(
                self._parser, self._settings, data, data_len
            )
            if self.upgrade:
                raise ConnectionUpgrade(parsed)
            elif parsed != data_len:
                if self.http_errno.name.startswith('cb_'):
                    # an error occurred in a callback, re-raise it here
                    callback_name = self.http_errno.name.replace('cb_', 'on_')
                    callback = getattr(self, callback_name)
                    raise callback.last_exception
                else:
                    raise HTTPParserError(self.http_errno, parsed)
            # these can't communicate failure so we have to use a side-channel
            elif self.on_headers_complete.last_exception:
                raise self.on_headers_complete.last_exception
            elif self.on_message_complete.last_exception:
                raise self.on_message_complete.last_exception
            return parsed

    @contextmanager
    def _callback_exception(self):
        try:
            yield
        finally:
            self.on_message_begin.__func__.last_exception = None
            self.on_url.__func__.last_exception = None
            self.on_status.__func__.last_exception = None
            self.on_header_field.__func__.last_exception = None
            self.on_header_value.__func__.last_exception = None
            self.on_headers_complete.__func__.last_exception = None
            self.on_body.__func__.last_exception = None
            self.on_message_complete.__func__.last_exception = None

    def on_message_begin(self):
        """
        Called when a new message begins.
        """

    def on_url(self, data):
        """
        Called when the url is being received.
        """

    def on_status(self, data):
        """
        Called when the status was received.
        """

    def on_header_field(self, data):
        """
        Called when a header field is being received.
        """

    def on_header_value(self, data):
        """
        Called when a header value is being received.
        """

    def on_headers_complete(self):
        """
        Called when all headers have been received.

        In a `ParserType.response` parser, `1` may be returned to tell the
        parser that no body will follow.
        """

    def on_body(self, data):
        """
        Called when the body is being received.
        """

    def on_message_complete(self):
        """
        Called when the message is completed.
        """


def parse_url(data, is_connect):
    """
    Parses the given `data` and returns a :class:`URL` instance. `is_connect`
    should be `True`, if the url should be parsed as defined in a `CONNECT`
    request, `False` otherwise.

    If the given `data` is not a url -- possibly under the limitation imposed
    by `is_connect` -- a :exc:`ValueError` is raised.
    """
    if not isinstance(data, bytes):
        raise TypeError('expected bytes, received {!r}'.format(data))
    url = ffi.new('struct http_parser_url*')
    failed = lib.http_parser_parse_url(
        data, len(data), int(bool(is_connect)), url
    )
    if failed:
        raise ValueError('not a url: {!r}'.format(data))
    fields = []
    for i, field_name in enumerate(URL._fields):
        if url.field_set & (1 << i):
            offset = url.field_data[i].off
            length = url.field_data[i].len
            field = data[offset:offset+length]
            fields.append(field)
        else:
            fields.append(None)
    return URL(*fields)


class URL(namedtuple('URL', 'schema host port path query fragment userinfo')):
    """
    A named tuple representing the components of a url.
    """
