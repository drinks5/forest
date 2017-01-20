from .request cimport Request
from .router cimport Router

cdef class HttpProtocolMixin:
    cdef:
        object loop
        object router
        object signal
        set connections
        int request_timeout
        object parser
        object _timeout_handler
        float _last_request_time
        bytes url
        list headers
        object _request_handler_task
        int _total_request_size
        int request_max_size
        object time
        Request request
