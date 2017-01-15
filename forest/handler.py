from .response import text
from .utils import log
from .routers import Router


class Handler(object):

    async def request(self, request, response_writer):
        log.info('request: %s, %s' % (request, response_writer))
        response = Router.get(request)
        log.info('response: %s' % response)
        return text(response_writer(response))

    def error(self, request, exception):
        response = text(str(request) + str(exception))
        return response
