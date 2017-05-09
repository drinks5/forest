# -*- coding: utf-8 -*-

# Copyright (C) 2016, Maximilian Köhl <mail@koehlma.de>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License version 3 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, unicode_literals, division, absolute_import
import errno
import abc
import signal
import collections
import sys
import socket
import threading
import traceback
import warnings
import weakref
import asyncio

from . import base, common, error, library, events
from .dns import AddressFamilies, getaddrinfo
from .library import ffi, lib
from .check import Check
from .handles.tcp import TCP
from .server import Server
from .common import ssl_SSLContext, has_SO_REUSEPORT, col_Iterable, logger, iscoroutinefunction, iscoroutine

def _is_dgram_socket(sock):
    # Linux's socket.type is a bitmask that can include extra info
    # about socket, therefore we can't do simple
    # `sock_type == socket.SOCK_DGRAM`.
    return (sock.type & socket.SOCK_DGRAM) == socket.SOCK_DGRAM


class RunModes(common.Enumeration):
    """
    Run modes to control the behavior of :func:`uv.Loop.run`.
    """

    DEFAULT = lib.UV_RUN_DEFAULT
    """
    Run the event loop until there are no more active and referenced
    handles or requests. :func:`uv.Loop.run` returns `True` if
    :func:`uv.Loop.stop` was called and there are still active
    handles or requests and `False` otherwise.

    :type: uv.RunModes
    """

    ONCE = lib.UV_RUN_ONCE
    """
    Poll for IO once. Note that :func:`uv.Loop.run` will block if there
    are no pending callbacks. :func:`uv.Loop.run` returns `True` if
    there are still active handles or requests which means the event
    loop should run again sometime in the future.

    :type: uv.RunModes
    """

    NOWAIT = lib.UV_RUN_NOWAIT
    """
    Poll for IO once but do not block if there are no pending
    callbacks. :func:`uv.Loop.run` returns `True` if there are still
    active handles or requests which means the event loop should run
    again sometime in the future.

    :type: uv.RunModes
    """


def default_excepthook(loop, exc_type, exc_value, exc_traceback):  # pragma: no cover
    """
    Default excepthook. Prints a traceback and stops the event loop to
    prevent deadlocks and livelocks.

    :param loop:
        event loop the callback belongs to
    :param exc_type:
        exception class of the thrown exception
    :param exc_value:
        exception instance of the thrown exception
    :param exc_traceback:
        traceback to the stack frame where the exception occoured

    :type loop:
        uv.Loop
    :type exc_type:
        Subclass[Exception]
    :type exc_value:
        Exception
    :type exc_traceback:
        traceback
    """
    print('Exception happened during callback execution!', file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    loop.stop()


class Allocator(common.with_metaclass(abc.ABCMeta)):
    """
    Abstract base class for read buffer allocators. Allows swappable
    allocation strategies and custom read result types.

    .. warning::
        This class exposes some details of the underlying CFFI based
        wrapper — use it with caution. Any errors in the allocator
        might lead to unpredictable behavior.
    """

    @abc.abstractmethod
    def allocate(self, handle, suggested_size, uv_buffer):
        """
        Called if libuv needs a new read buffer. The allocated chunk of
        memory has to be assigned to `uv_buf.base` and the length of
        the chunk to `uv_buf.len` use :func:`library.uv_buffer_set()`
        for assigning. Base might be `NULL` which triggers an `ENOBUFS`
        error in the read callback.

        :param handle:
            handle caused the read
        :param suggested_size:
            suggested buffer size
        :param uv_buffer:
            uv target buffer

        :type handle:
            uv.Handle
        :type suggested_size:
            int
        :type uv_buffer:
            ffi.CData[uv_buf_t]
        """

    @abc.abstractmethod
    def finalize(self, handle, length, uv_buffer):
        """
        Called in the read callback to access the read buffer's data.
        The result of this call is directly passed to the user's read
        callback which allows to use a custom read result type.

        :param handle:
            handle caused the read
        :param length:
            length of bytes read
        :param uv_buffer:
            uv buffer used for reading

        :type handle:
            uv.Handle
        :type length:
            int
        :type uv_buffer:
            ffi.CData[uv_buf_t]

        :return:
            buffer's data (default type is :class:`bytes`)
        :rtype:
            Any | bytes
        """


class DefaultAllocator(Allocator):
    """
    Default read buffer allocator which only uses one buffer and copies
    the data to a python :class:`bytes` object after reading.
    """

    def __init__(self, buffer_size=2**16):
        """
        :param buffer_size:
            size of the internal buffer

        :type buffer_size:
            int
        """
        self.buffer_size = buffer_size
        self.buffer_in_use = False

        self.c_buffer = ffi.new('char[]', self.buffer_size)

    def allocate(self, handle, suggested_size, uv_buffer):
        if self.buffer_in_use:  # pragma: no cover
            # this should never happen because lib uv reads the data right
            # before the execution of the read callback even if there are
            # multiple sockets ready for reading
            library.uv_buffer_set(uv_buffer, ffi.NULL, 0)
        else:
            library.uv_buffer_set(uv_buffer, self.c_buffer, self.buffer_size)
        self.buffer_in_use = True

    def finalize(self, uv_handle, length, uv_buffer):
        self.buffer_in_use = False
        c_base = library.uv_buffer_get(uv_buffer).base
        return bytes(ffi.buffer(c_base, length)) if length > 0 else b''


@ffi.callback('uv_walk_cb')
def uv_walk_cb(uv_handle, c_handles_set):
    handle = base.BaseHandle.detach(uv_handle)
    if handle is not None:
        ffi.from_handle(c_handles_set).add(handle)


class Loop(object):
    """
    The event loop is the central part of this library. It takes care
    of polling for IO and scheduling callbacks to be run based on
    different sources of events.

    :raises RuntimeError:
        error while initializing global default loop
    :raises UVError:
        error initializing the new event loop

    :param allocator:
        read buffer allocator
    :param buffer_size:
        size of the default allocators read buffer
    :param default:
        instantiate the default loop

    :type allocator:
        uv.loop.Allocator
    :type buffer_size:
        int
    :type default:
        bool
    """

    _global_lock = threading.RLock()
    _thread_locals = threading.local()
    _default = None

    @classmethod
    def get_default(cls, instantiate=True, **keywords):
        """
        Get the default (across multiple threads) event loop. Note that
        although this returns the same loop across multiple threads
        loops are not thread safe. Normally there is one thread running
        the default loop and others interfering with it trough
        :class:`uv.Async` handles or :func:`uv.Loop.call_later`.

        :param instantiate:
            instantiate the default event loop if it does not exist

        :type instantiate:
            bool

        :return:
            global default loop
        :rtype:
            Loop
        """
        with cls._global_lock:
            if cls._default is None and instantiate:
                Loop._default = Loop(default=True, **keywords)
            return Loop._default

    @classmethod
    def get_current(cls, instantiate=True, **keywords):
        """
        Get the current (thread local) default event loop. Loops
        register themselves as current loop on instantiation and in
        their :func:`uv.Loop.run` method.

        :param instantiate:
            instantiate a new loop if there is no current loop

        :type instantiate:
            bool

        :return:
            current thread's default loop
        :rtype:
            Loop
        """
        loop = getattr(cls._thread_locals, 'loop', None)
        if loop is None and instantiate:
            return cls(**keywords)
        return loop

    def __init__(self, allocator=None, buffer_size=2**16, default=False):
        if default:
            with Loop._global_lock:
                if Loop._default:
                    raise RuntimeError('global default loop already instantiated')
                Loop._default = self

        self.base_loop = base.BaseLoop(self, default)
        self.uv_loop = self.base_loop.uv_loop

        self.allocator = allocator or DefaultAllocator(buffer_size)

        self.excepthook = default_excepthook

        self._debug_exception_handler_cnt = 0
        if hasattr(sys, 'get_asyncgen_hooks'):
            # Python >= 3.6
            # A weak set of all asynchronous generators that are
            # being iterated by the loop.
            self._asyncgens = weakref.WeakSet()
        else:
            self._asyncgens = None

        # Set to True when `loop.shutdown_asyncgens` is called.
        self._asyncgens_shutdown_called = False

        self.handler_check__exec_writes = UVCheck.new(
            self,
            new_MethodHandle(
                self, "loop._exec_queued_writes",
                <method_t>self._exec_queued_writes, self))

        """
        If an exception occurs during the execution of a callback this
        excepthook is called with the corresponding event loop and
        exception details. The default behavior is to print the
        traceback to stderr and stop the event loop. To override the
        default behavior assign a custom function to this attribute.

        .. note::
            If the excepthook raises an exception itself the program
            would be in an undefined state. Therefore it terminates
            with `sys.exit(1)` in that case immediately.


        .. function:: excepthook(loop, exc_type, exc_value, exc_traceback)

            :param loop:
                corresponding event loop
            :param exc_type:
                exception type (subclass of :class:`BaseException`)
            :param exc_value:
                exception instance
            :param exc_traceback:
                traceback which encapsulates the call stack at the
                point where the exception originally occurred

            :type loop:
                uv.Loop
            :type exc_type:
                type
            :type exc_value:
                BaseException
            :type exc_traceback:
                traceback


        :readonly:
            False
        :type:
            ((uv.Loop, type, Exception, traceback.Traceback) -> None) |
            ((Any, uv.Loop, type, Exception, traceback.Traceback) -> None)
        """
        self.exc_type = None
        """
        Type of last exception handled by the excepthook.

        :readonly:
            True
        :type:
            type
        """
        self.exc_value = None
        """
        Instance of last exception handled by the excepthook.

        :readonly:
            True
        :type:
            BaseException
        """
        self.exc_traceback = None
        """
        Traceback of the last exception handled by the excepthook.

        :readonly:
            True
        :type:
            traceback
        """

        self.make_current()
        self.pending_structures = set()
        self.pending_callbacks = collections.deque()
        self.pending_callbacks_lock = threading.RLock()
        self._debug = False

    @property
    def closed(self):
        """
        True if and only if the loop has been closed.

        :readonly:
            True
        :rtype:
            bool
        """
        return self.base_loop.closed

    @property
    def alive(self):
        """
        `True` if there are active and referenced handles running on
        the loop, `False` otherwise.

        :readonly:
            True
        :rtype:
            bool
        """
        if self.closed:
            return False
        return bool(lib.uv_loop_alive(self.uv_loop))

    @property
    def now(self):
        """
        Current internal timestamp in milliseconds. The timestamp
        increases monotonically from some arbitrary point in time.

        :readonly:
            True
        :rtype:
            int
        """
        if self.closed:
            raise error.ClosedLoopError()
        return lib.uv_now(self.uv_loop)

    @property
    def handles(self):
        """
        Set of all handles running on the loop.

        :readonly:
            True
        :rtype:
            set
        """
        handles = set()
        if not self.closed:
            lib.uv_walk(self.uv_loop, uv_walk_cb, ffi.new_handle(handles))
        return handles

    def fileno(self):
        """
        Get the file descriptor of the backend. This is only supported
        on kqueue, epoll and event ports.

        :raises uv.UVError:
            error getting file descriptor
        :raises uv.ClosedLoopError:
            loop has already been closed

        :returns:
            backend file descriptor
        :rtype:
            int
        """
        if self.closed:
            raise error.ClosedLoopError()
        return lib.uv_backend_fd(self.uv_loop)

    def make_current(self):
        """
        Make the loop the current thread local default loop.
        """
        Loop._thread_locals.loop = self

    def update_time(self):
        """
        Update the event loop’s concept of “now”. Libuv caches the
        current time at the start of the event loop tick in order to
        reduce the number of time-related system calls.

        :raises uv.ClosedLoopError:
            loop has already been closed

        .. note::
            You won’t normally need to call this function unless you
            have callbacks that block the event loop for longer periods
            of time, where “longer” is somewhat subjective but probably
            on the order of a millisecond or more.
        """
        if self.closed:
            raise error.ClosedLoopError()
        lib.uv_update_time(self.uv_loop)

    def get_timeout(self):
        """
        Get the poll timeout. The return value is in milliseconds, or
        -1 for no timeout.

        :raises uv.ClosedLoopError:
            loop has already been closed

        :returns:
            backend timeout in milliseconds
        :rtype:
            int
        """
        if self.closed:
            raise error.ClosedLoopError()
        return lib.uv_backend_timeout(self.uv_loop)

    def run(self, mode=RunModes.DEFAULT):
        """
        Run the loop in the specified mode.

        :raises uv.ClosedLoopError:
            loop has already been closed

        :param mode:
            run mode

        :type mode:
            uv.RunModes

        :returns:
            run mode specific return value
        :rtype:
            bool
        """
        if self.closed:
            raise error.ClosedLoopError()
        self.make_current()
        return bool(lib.uv_run(self.uv_loop, mode))

    def stop(self):
        """
        Stop the event loop, causing :func:`uv.Loop.run` to end as soon
        as possible. This will happen not sooner than the next loop
        iteration. If this method was called before blocking for IO,
        the loop will not block for IO on this iteration.
        """
        if self.closed:
            return
        lib.uv_stop(self.uv_loop)

    def close(self):
        """
        Closes all internal loop resources. This method must only be
        called once the loop has finished its execution or it will
        raise :class:`uv.error.ResourceBusyError`.

        .. note::
            Loops are automatically closed when they are garbage
            collected. However because the exact time this happens is
            non-deterministic you should close them explicitly.

        :raises uv.UVError:
            error while closing the loop
        :raises uv.error.ResourceBusyError:
            loop is currently running or there are pending operations
        """
        code = self.base_loop.close()
        if code != error.StatusCodes.SUCCESS:
            raise error.UVError(code)
        if Loop._thread_locals.loop is self:
            Loop._thread_locals.loop = None

    def close_all_handles(self, on_closed=None):
        """
        Close all handles.

        :param on_closed:
            callback which should run after a handle has been closed
            (overrides the current callback if specified)

        :type on_closed:
            ((uv.Handle) -> None) | ((Any, uv.Handle) -> None)
        """
        for handle in self.handles:
            handle.close(on_closed)

    def call_later(self, callback, *arguments, **keywords):
        """
        Schedule a callback to run at some later point in time. The
        callback does not keep the loop alive if there a no other
        active handles running on the loop.

        This method is thread safe.

        :param callback:
            callback which should run at some later point in time
        :param arguments:
            arguments that should be passed to the callback
        :param keywords:
            keyword arguments that should be passed to the callback

        :type callback:
            callable
        :type arguments:
            tuple
        :type keywords:
            dict
        """
        with self.pending_callbacks_lock:
            self.pending_callbacks.append((callback, arguments, keywords))
            self.base_loop.wakeup()

    def reset_exception(self):
        """
        Reset the last exception caught by the excepthook.
        """
        self.exc_type = None
        self.exc_value = None
        self.exc_traceback = None

    def on_wakeup(self):
        """
        Called after the event loop has been woken up.

         .. warning::
            This method is only for internal purposes and is not part
            of the official API. You should never call it directly!
        """
        try:
            while True:
                with self.pending_callbacks_lock:
                    callback, arguments, keywords = self.pending_callbacks.popleft()
                try:
                    callback(*arguments, **keywords)
                except Exception:
                    self.handle_exception()
        except IndexError:
            pass

    def handle_exception(self):
        """
        Handle the current exception using the excepthook.

        .. warning::
            This method is only for internal purposes and is not part
            of the official API. You should never call it directly!
        """
        self.exc_type, self.exc_value, self.exc_traceback = sys.exc_info()
        try:
            self.excepthook(self, self.exc_type, self.exc_value, self.exc_traceback)
        except Exception:  # pragma: no cover
            # this should never happen during normal operation but if it does the
            # program would be in an undefined state, so exit immediately
            try:
                print('[CRITICAL] error while executing excepthook!', file=sys.stderr)
                traceback.print_exc()
            finally:
                sys.exit(1)

    def structure_set_pending(self, structure):
        """
        Add a structure to the set of pending structures.

        .. warning::
            This method is only for internal purposes and is not part
            of the official API. You should never call it directly!

        :type structure:
            uv.Handle | uv.Request
        """
        self.pending_structures.add(structure)

    def structure_clear_pending(self, structure):
        """
        Remove a structure from the set of pending structures.

        .. warning::
            This method is only for internal purposes and is not part
            of the official API. You should never call it directly!

        :type structure:
            uv.Handle | uv.Request
        """
        try:
            self.pending_structures.remove(structure)
        except KeyError:
            pass

    def structure_is_pending(self, structure):
        """
        Return true if and only if the structure is pending.

        .. warning::
            This method is only for internal purposes and is not part
            of the official API. You should never call it directly!

        :type structure:
            uv.Handle | uv.Request
        """
        return structure in self.pending_structures

    async def create_server(self, protocol_factory, host=None, port=None,
                            *,
                            family=AddressFamilies.UNKNOWN,
                            flags=socket.AI_PASSIVE,
                            sock=None,
                            backlog=100,
                            ssl=None,
                            reuse_address=None,  # ignored, libuv sets it
                            reuse_port=None):
        if sock is not None and sock.family == AddressFamilies.UNIX:
            if host is not None or port is not None:
                raise ValueError(
                    'host/port and sock can not be specified at the same time')
            return await self.create_unix_server(
                protocol_factory, sock=sock, ssl=ssl)
        server = Server(self)

        if ssl is not None and not isinstance(ssl, ssl_SSLContext):
            raise TypeError('ssl argument must be an SSLContext or None')
        if host is not None or port is not None:
            if sock is not None:
                raise ValueError(
                    'host/port and sock can not be specified at the same time')

            reuse_port = bool(reuse_port)
            if reuse_port and not has_SO_REUSEPORT:
                raise ValueError(
                    'reuse_port not supported by socket module')

            if host == '':
                hosts = [None]
            elif (isinstance(host, str) or not isinstance(host, col_Iterable)):
                hosts = [host]
            else:
                hosts = host
            info = getaddrinfo(host, port, family,
                                     socket.SOCK_STREAM, 0, flags,
                                     0, self)


            tcp = self._create_server(
                (host, port), protocol_factory, server,
                ssl, reuse_port, backlog)

            server._add_server(tcp)
        return server

    def _create_server(self, addr, protocol_factory, server, ssl, reuse_port, backlog):
        tcp = TCP()
        bind_flags = 0
        try:
            tcp.bind(addr, bind_flags)
            tcp.listen(backlog)
        except OSError as err:
            tcp.close()
            raise
        except:
            tcp.close()
            raise
        return tcp

    def run_forever(self):
        """Run the event loop until stop() is called."""
        self._check_closed()
        mode = lib.UV_RUN_DEFAULT
        if self._stopping:
            # loop.stop() was called right before loop.run_forever().
            # This is how asyncio loop behaves.
            mode = lib.UV_RUN_NOWAIT
        self._set_coroutine_wrapper(self._debug)
        if self._asyncgens is not None:
            old_agen_hooks = sys.get_asyncgen_hooks()
            sys.set_asyncgen_hooks(firstiter=self._asyncgen_firstiter_hook,
                                   finalizer=self._asyncgen_finalizer_hook)
        try:
            self._run(mode)
        finally:
            self._set_coroutine_wrapper(False)
            if self._asyncgens is not None:
                sys.set_asyncgen_hooks(*old_agen_hooks)

    def _set_coroutine_wrapper(self, enabled):
        enabled = bool(enabled)
        if self._coroutine_wrapper_set == enabled:
            return

    def get_exception_handler(self):
        """Return an exception handler, or None if the default one is in use.
        """
        return self._exception_handler

    def set_exception_handler(self, handler):
        """Set handler as the new event loop exception handler.

        If handler is None, the default exception handler will
        be set.

        If handler is a callable object, it should have a
        signature matching '(loop, context)', where 'loop'
        will be a reference to the active event loop, 'context'
        will be a dict object (see `call_exception_handler()`
        documentation for details about context).
        """
        if handler is not None and not callable(handler):
            raise TypeError('A callable object or None is expected, '
                            'got {!r}'.format(handler))
        self._exception_handler = handler

    def default_exception_handler(self, context):
        """Default exception handler.

        This is called when an exception occurs and no exception
        handler is set, and can be called by a custom exception
        handler that wants to defer to the default behavior.

        The context parameter has the same meaning as in
        `call_exception_handler()`.
        """
        message = context.get('message')
        if not message:
            message = 'Unhandled exception in event loop'

        exception = context.get('exception')
        if exception is not None:
            exc_info = (type(exception), exception, exception.__traceback__)
        else:
            exc_info = False

        if ('source_traceback' not in context
        and self._current_handle is not None
        and self._current_handle._source_traceback):
            context['handle_traceback'] = self._current_handle._source_traceback

        log_lines = [message]
        for key in sorted(context):
            if key in {'message', 'exception'}:
                continue
            value = context[key]
            if key == 'source_traceback':
                tb = ''.join(traceback.format_list(value))
                value = 'Object created at (most recent call last):\n'
                value += tb.rstrip()
            elif key == 'handle_traceback':
                tb = ''.join(traceback.format_list(value))
                value = 'Handle created at (most recent call last):\n'
                value += tb.rstrip()
            else:
                value = repr(value)
            log_lines.append('{}: {}'.format(key, value))

        logger.error('\n'.join(log_lines), exc_info=exc_info)

    def call_exception_handler(self, context):
        """Call the current event loop's exception handler.

        The context argument is a dict containing the following keys:

        - 'message': Error message;
        - 'exception' (optional): Exception object;
        - 'future' (optional): Future instance;
        - 'handle' (optional): Handle instance;
        - 'protocol' (optional): Protocol instance;
        - 'transport' (optional): Transport instance;
        - 'socket' (optional): Socket instance;
        - 'asyncgen' (optional): Asynchronous generator that caused
                                 the exception.

        New keys maybe introduced in the future.

        Note: do not overload this method in an event loop subclass.
        For custom exception handling, use the
        `set_exception_handler()` method.
        """
        if self._debug:
            self._debug_exception_handler_cnt += 1
        if self._exception_handler is None:
            try:
                self.default_exception_handler(context)
            except Exception:
                # Second protection layer for unexpected errors
                # in the default implementation, as well as for subclassed
                # event loops with overloaded "default_exception_handler".
                logger.error('Exception in default exception handler',
                             exc_info=True)
        else:
            try:
                self._exception_handler(self, context)
            except Exception as exc:
                # Exception in the user set custom exception handler.
                try:
                    # Let's try default handler.
                    self.default_exception_handler({
                        'message': 'Unhandled error in exception handler',
                        'exception': exc,
                        'context': context,
                    })
                except Exception:
                    # Guard 'default_exception_handler' in case it is
                    # overloaded.
                    logger.error('Exception in default exception handler '
                                 'while handling an unexpected error '
                                 'in custom exception handler',
                                 exc_info=True)

    def get_debug(self):
        return self._debug

    def set_debug(self, enabled):
        self._debug = enabled

        if self.is_running():
            self._set_coroutine_wrapper(enabled)

    # TODO
    def _setup_signals(self):
        pass
        #  self._ssock, self._csock = socket_socketpair()
        #  self._ssock.setblocking(False)
        #  self._csock.setblocking(False)
        #  try:
            #  signal_set_wakeup_fd(self._csock.fileno())
        #  except ValueError:
            #  # Not the main thread
            #  self._ssock.close()
            #  self._csock.close()
            #  self._ssock = self._csock = None
            #  return

        #  self._add_reader(
            #  self._ssock.fileno(),
            #  new_MethodHandle(
                #  self,
                #  "Loop._read_from_self",
                #  self._read_from_self,
                #  self))

        #  self._signal_handlers = {}

    def add_signal_handler(self, sig, callback, *args):
        """Add a handler for a signal.  UNIX only.

        Raise ValueError if the signal number is invalid or uncatchable.
        Raise RuntimeError if there is a problem setting up the handler.
        """
        if self._signal_handlers is None:
            self._setup_signals()
            if self._signal_handlers is None:
                raise ValueError('set_wakeup_fd only works in main thread')

        if (iscoroutine(callback)
        or iscoroutinefunction(callback)):
            raise TypeError("coroutines cannot be used "
                            "with add_signal_handler()")
        self._check_signal(sig)
        self._check_closed()
        try:
            # set_wakeup_fd() raises ValueError if this is not the
            # main thread.  By calling it early we ensure that an
            # event loop running in another thread cannot add a signal
            # handler.
            signal.set_wakeup_fd(self._csock.fileno())
        except (ValueError, OSError) as exc:
            raise RuntimeError(str(exc))

        handle = events.Handle(callback, args, self)
        self._signal_handlers[sig] = handle

        try:
            # Register a dummy signal handler to ask Python to write the signal
            # number in the wakup file descriptor. _process_self_data() will
            # read signal numbers from this file descriptor to handle signals.
            signal.signal(sig, _sighandler_noop)

            # Set SA_RESTART to limit EINTR occurrences.
            signal.siginterrupt(sig, False)
        except OSError as exc:
            del self._signal_handlers[sig]
            if not self._signal_handlers:
                try:
                    signal.set_wakeup_fd(-1)
                except (ValueError, OSError) as nexc:
                    logger.info('set_wakeup_fd(-1) failed: %s', nexc)

            if exc.errno == errno.EINVAL:
                raise RuntimeError('sig {} cannot be caught'.format(sig))
            else:
                raise

    def remove_signal_handler(self, sig):
        """Remove a handler for a signal.  UNIX only.

        Return True if a signal handler was removed, False if not.
        """
        self._check_signal(sig)

        if self._signal_handlers is None:
            return False

        try:
            del self._signal_handlers[sig]
        except KeyError:
            return False

        if sig == lib.SIGINT:
            handler = signal.default_int_handler
        else:
            handler = signal.SIG_DFL

        try:
            signal.signal(sig, handler)
        except OSError as exc:
            if exc.errno == errno.EINVAL:
                raise RuntimeError('sig {} cannot be caught'.format(sig))
            else:
                raise
        return True
    async def create_datagram_endpoint(self, protocol_factory,
                                 local_addr=None, remote_addr=None, *,
                                 family=0, proto=0, flags=0,
                                 reuse_address=None, reuse_port=None,
                                 allow_broadcast=None, sock=None):
        """Create datagram connection."""
        if sock is not None:
            if not _is_dgram_socket(sock):
                raise ValueError(
                    'A UDP Socket was expected, got {!r}'.format(sock))
            if (local_addr or remote_addr or
                    family or proto or flags or
                    reuse_address or reuse_port or allow_broadcast):
                # show the problematic kwargs in exception msg
                opts = dict(local_addr=local_addr, remote_addr=remote_addr,
                            family=family, proto=proto, flags=flags,
                            reuse_address=reuse_address, reuse_port=reuse_port,
                            allow_broadcast=allow_broadcast)
                problems = ', '.join(
                    '{}={}'.format(k, v) for k, v in opts.items() if v)
                raise ValueError(
                    'socket modifier keyword arguments can not be used '
                    'when sock is specified. ({})'.format(problems))
            sock.setblocking(False)
            r_addr = None
        else:
            if not (local_addr or remote_addr):
                if family == 0:
                    raise ValueError('unexpected address family')
                addr_pairs_info = (((family, proto), (None, None)),)
            else:
                # join address by (family, protocol)
                addr_infos = collections.OrderedDict()
                for idx, addr in ((0, local_addr), (1, remote_addr)):
                    if addr is not None:
                        assert isinstance(addr, tuple) and len(addr) == 2, (
                            '2-tuple is expected')

                        infos = yield from _ensure_resolved(
                            addr, family=family, type=socket.SOCK_DGRAM,
                            proto=proto, flags=flags, loop=self)
                        if not infos:
                            raise OSError('getaddrinfo() returned empty list')

                        for fam, _, pro, _, address in infos:
                            key = (fam, pro)
                            if key not in addr_infos:
                                addr_infos[key] = [None, None]
                            addr_infos[key][idx] = address

                # each addr has to have info for each (family, proto) pair
                addr_pairs_info = [
                    (key, addr_pair) for key, addr_pair in addr_infos.items()
                    if not ((local_addr and addr_pair[0] is None) or
                            (remote_addr and addr_pair[1] is None))]

                if not addr_pairs_info:
                    raise ValueError('can not get address information')

            exceptions = []

            if reuse_address is None:
                reuse_address = os.name == 'posix' and sys.platform != 'cygwin'

            for ((family, proto),
                 (local_address, remote_address)) in addr_pairs_info:
                sock = None
                r_addr = None
                try:
                    sock = socket.socket(
                        family=family, type=socket.SOCK_DGRAM, proto=proto)
                    if reuse_address:
                        sock.setsockopt(
                            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    if reuse_port:
                        _set_reuseport(sock)
                    if allow_broadcast:
                        sock.setsockopt(
                            socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.setblocking(False)

                    if local_addr:
                        sock.bind(local_address)
                    if remote_addr:
                        yield from self.sock_connect(sock, remote_address)
                        r_addr = remote_address
                except OSError as exc:
                    if sock is not None:
                        sock.close()
                    exceptions.append(exc)
                except:
                    if sock is not None:
                        sock.close()
                    raise
                else:
                    break
            else:
                raise exceptions[0]

        protocol = protocol_factory()
        waiter = self.create_future()
        transport = self._make_datagram_transport(
            sock, protocol, r_addr, waiter)
        if self._debug:
            if local_addr:
                logger.info("Datagram endpoint local_addr=%r remote_addr=%r "
                            "created: (%r, %r)",
                            local_addr, remote_addr, transport, protocol)
            else:
                logger.debug("Datagram endpoint remote_addr=%r created: "
                             "(%r, %r)",
                             remote_addr, transport, protocol)

        try:
            yield from waiter
        except:
            transport.close()
            raise

        return transport, protocol


    def _check_signal(self, sig):
        """Internal helper to validate a signal.

        Raise ValueError if the signal number is invalid or uncatchable.
        Raise RuntimeError if there is a problem setting up the handler.
        """
        if not isinstance(sig, int):
            raise TypeError('sig must be an int, not {!r}'.format(sig))

        if not (1 <= sig < signal.NSIG):
            raise ValueError(
                'sig {} out of range(1, {})'.format(sig, signal.NSIG))

    def _check_closed(self):
        if self._closed == 1:
            raise RuntimeError('Event loop is closed')

    def _check_running(self):
        if self._running == 1:
            raise RuntimeError('this event loop is already running.')


    def _asyncgen_firstiter_hook(self, agen):
        if self._asyncgens_shutdown_called:
            warnings.warn(
                "asynchronous generator {!r} was scheduled after "
                "loop.shutdown_asyncgens() call".format(agen),
                ResourceWarning, source=self)

        self._asyncgens.add(agen)

    def _asyncgen_finalizer_hook(self, agen):
        self._asyncgens.discard(agen)
        if not self.is_closed():
            self.create_task(agen.aclose())
            # Wake up the loop if the finalizer was called from
            # a different thread.
            self.handler_async.send()

    def _run(self, mode):
        self._check_closed()
        self._check_running()
        if hasattr(asyncio, '_get_running_loop') and asyncio._get_running_loop() is not None:
            raise RuntimeError(
                'Cannot run the event loop while another loop is running')
        if self._signal_handlers is None:
            self._setup_signals()
        self._last_error = None
        self._thread_id = threading.get_ident()
        self._thread_is_main = threading.main_thread().ident == self._thread_id
        self._running = 1
        self.handler_check__exec_writes.start()
        self.handler_idle.start()

        getattr(asyncio, '_set_running_loop', None) is not None and asyncio._set_running_loop(self)
        try:
            self.__run(mode)
        finally:
            getattr(asyncio, '_set_running_loop', None) is not None and asyncio._set_running_loop(None)

        self.handler_check__exec_writes.stop()
        self.handler_idle.stop()

        self._thread_is_main = 0
        self._thread_id = 0
        self._running = 0
        self._stopping = 0

        if self._last_error is not None:
            # The loop was stopped with an error with 'loop._stop(error)' call
            raise self._last_error

def _sighandler_noop(signum, frame):
    """Dummy signal handler."""
    pass
