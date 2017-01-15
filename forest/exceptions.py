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
