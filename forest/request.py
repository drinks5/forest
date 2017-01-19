from urllib.parse import parse_qsl
import ujson as json
from httptools import parse_url
from .exceptions import InvalidUsage


class Request:

    # def __init__(self, bytes url_bytes, object  headers, str version, object method):
    def __init__(self, url_bytes, headers, version, method):
        url_parsed = parse_url(url_bytes)
        self.path = url_parsed.path.decode('utf8')
        self.headers = headers
        self.version = version
        self.method = method
        self.query_string = None
        if url_parsed.query:
            self.query_string = url_parsed

        self.body = None
        self.parsed_json = None

    @property
    def data(self):
        if self.query_string is not None:
            return dict(parse_qsl(self.query_string))
        if self.parsed_json is None:
            try:
                self.parsed_json = json.loads(self.body)
                return self.parsed_json
            except Exception:
                raise InvalidUsage("Failed when parsing body as json")
