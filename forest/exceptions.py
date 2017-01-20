from .response import ALL_STATUS_CODES

class SanicException(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class HttpParserError(Exception):
    pass


class ServerError(Exception):
    pass


class InvalidUsage(Exception):
    pass


class PayloadTooLarge(Exception):
    pass


class RequestTimeout(Exception):
    pass


class RouterError(Exception):
    pass


class HttpError(Exception):
    def __init__(self, status_code, *args, **kwargs):
        reason = ALL_STATUS_CODES[status_code]
        super().__init__(reason)
