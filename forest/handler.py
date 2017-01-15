from .response import text, exception
from .utils import log
from .routers import Router


class Handler(object):

    async def request(self, request, response_writer):
        log.info('request: %s, %s' % (request, response_writer))
        handler = Router.get(request)
        if not handler:
            return response_writer(exception(404))
        response = handler(request)
        log.info('response: %s' % response)
        return response_writer(response)

    def error(self, request, exception):
        response = text(str(request) + str(exception))
        return response
