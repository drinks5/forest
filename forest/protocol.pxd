from .handler import Handler

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

    # def connection_made(self, object transport)

    # def connection_lost(self, object exc)

    # def connection_timeout(self)

    # def data_received(self, object data)

    # def on_url(self, bytes url)

    # def on_header(self, bytes name, bytes value)

    # def on_headers_complete(self)

    # def on_body(self, bytes body)

    # def on_message_complete(self)

    # def write_response(self, response)

    # def write_error(self, exception)

    # def bail_out(self, message)

    # def cleanup(self)

    # def close_if_idle(self)
