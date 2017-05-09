# coding: utf-8
"""
    test_httpparser
    ~~~~~~~~~~~~~~~

    Tests for the httpparser package.

    These tests are in part based on the `test.c` file of the http-parser
    library.

    :copyright: 2014 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import pytest

from httpparser import (
    __version__, __version_info__, __http_parser_version__,
    __http_parser_version_info__, Method, Errno, ParserType, HTTPParserError,
    ConnectionUpgrade, HTTPParser, parse_url, URL
)


try:
    str = unicode
except NameError:
    pass


REQUESTS = {
    'CURL_GET': {
        'name': "curl get",
        'type': ParserType.request,
        'raw': (
            b'GET /test HTTP/1.1\r\n'
            b'User-Agent: curl/7.18.0 (i486-pc-linux-gnu) libcurl/7.18.0 OpenSSL/0.9.8g zlib/1.2.3.3 libidn/1.1\r\n'
            b'Host: 0.0.0.0=5000\r\n'
            b'Accept: */*\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/test',
        'request_url': b'/test',
        'num_headers': 3,
        'headers': [
            (b'User-Agent', b'curl/7.18.0 (i486-pc-linux-gnu) libcurl/7.18.0 OpenSSL/0.9.8g zlib/1.2.3.3 libidn/1.1'),
            (b'Host', b'0.0.0.0=5000'),
            (b'Accept', b'*/*')
        ],
        'body': b''
    },
    'FIREFOX_GET': {
        'name': "firefox get",
        'type': ParserType.request,
        'raw': (
            b'GET /favicon.ico HTTP/1.1\r\n'
            b'Host: 0.0.0.0=5000\r\n'
            b'User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008061015 Firefox/3.0\r\n'
            b'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n'
            b'Accept-Language: en-us,en;q=0.5\r\n'
            b'Accept-Encoding: gzip,deflate\r\n'
            b'Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\r\n'
            b'Keep-Alive: 300\r\n'
            b'Connection: keep-alive\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/favicon.ico',
        'request_url': b'/favicon.ico',
        'num_headers': 8,
        'headers': [
            (b'Host', b'0.0.0.0=5000'),
            (b'User-Agent', b'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008061015 Firefox/3.0'),
            (b'Accept', b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            (b'Accept-Language', b'en-us,en;q=0.5'),
            (b'Accept-Encoding', b'gzip,deflate'),
            (b'Accept-Charset', b'ISO-8859-1,utf-8;q=0.7,*;q=0.7'),
            (b'Keep-Alive', b'300'),
            (b'Connection', b'keep-alive'),
        ],
        'body': b''
    },
    'DUMBFUCK': {
        'name': "dumbfuck",
        'type': ParserType.request,
        'raw': (
            b'GET /dumbfuck HTTP/1.1\r\n'
            b'aaaaaaaaaaaaa:++++++++++\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/dumbfuck',
        'request_url': b'/dumbfuck',
        'num_headers': 1,
        'headers': [
            (b'aaaaaaaaaaaaa',  b'++++++++++')
        ],
        'body': b''
    },
    'FRAGMENT_IN_URI': {
        'name': "fragment in url",
        'type': ParserType.request,
        'raw': (
            b'GET /forums/1/topics/2375?page=1#posts-17408 HTTP/1.1\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': b'page=1',
        'fragment': b'posts-17408',
        'request_path': b'/forums/1/topics/2375',
        'request_url': b'/forums/1/topics/2375?page=1#posts-17408',
        'num_headers': 0,
        'body': b''
    },
    'GET_NO_HEADERS_NO_BODY': {
        'name': "get no headers no body",
        'type': ParserType.request,
        'raw': (
            b'GET /get_no_headers_no_body/world HTTP/1.1\r\n'
            b'\r\n'
        ),
       'should_keep_alive': True,
       'message_complete_on_eof': False,
       'http_major': 1,
       'http_minor': 1,
       'method': Method.get,
       'query_string': None,
       'fragment': None,
       'request_path': b'/get_no_headers_no_body/world',
       'request_url': b'/get_no_headers_no_body/world',
       'num_headers': 0,
       'body': b'',
    },
    'GET_ONE_HEADER_NO_BODY': {
        'name': "get one header no body",
        'type': ParserType.request,
        'raw': (
            b'GET /get_one_header_no_body HTTP/1.1\r\n'
            b'Accept: */*\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/get_one_header_no_body',
        'request_url': b'/get_one_header_no_body',
        'num_headers': 1,
        'headers': [
            (b'Accept' , b'*/*')
        ],
        'body': b''
    },
    'GET_FUNKY_CONTENT_LENGTH': {
        'name': "get funky content length body hello",
        'type': ParserType.request,
        'raw': (
            b'GET /get_funky_content_length_body_hello HTTP/1.0\r\n'
            b'conTENT-Length: 5\r\n'
            b'\r\n'
            b'HELLO'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 0,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/get_funky_content_length_body_hello',
        'request_url': b'/get_funky_content_length_body_hello',
        'num_headers': 1,
        'headers': [
            (b'conTENT-Length', b'5')
        ],
        'body': b'HELLO'
    },
    'POST_IDENTITY_BODY_WORLD': {
        'name': "post identity body world",
        'type': ParserType.request,
        'raw': (
            b'POST /post_identity_body_world?q=search#hey HTTP/1.1\r\n'
            b'Accept: */*\r\n'
            b'Transfer-Encoding: identity\r\n'
            b'Content-Length: 5\r\n'
            b'\r\n'
            b'World'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': b'q=search',
        'fragment': b'hey',
        'request_path': b'/post_identity_body_world',
        'request_url': b'/post_identity_body_world?q=search#hey',
        'num_headers': 3,
        'headers': [
            (b'Accept', b'*/*'),
            (b'Transfer-Encoding', b'identity'),
            (b'Content-Length', b'5'),
        ],
        'body': b'World'
    },
    'POST_CHUNKED_ALL_YOUR_BASE': {
        'name': "post - chunked body: all your base are belong to us",
        'type': ParserType.request,
        'raw': (
            b'POST /post_chunked_all_your_base HTTP/1.1\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'1e\r\nall your base are belong to us\r\n'
            b'0\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': None,
        'fragment': None,
        'request_path': b'/post_chunked_all_your_base',
        'request_url': b'/post_chunked_all_your_base',
        'num_headers': 1,
        'headers': [
            (b'Transfer-Encoding', b'chunked')
        ],
        'body': b'all your base are belong to us'
    },
    'TWO_CHUNKS_MULT_ZERO_END': {
        'name': "two chunks ; triple zero ending",
        'type': ParserType.request,
        'raw': (
            b'POST /two_chunks_mult_zero_end HTTP/1.1\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'5\r\nhello\r\n'
            b'6\r\n world\r\n'
            b'000\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': None,
        'fragment': None,
        'request_path': b'/two_chunks_mult_zero_end',
        'request_url': b'/two_chunks_mult_zero_end',
        'num_headers': 1,
        'headers': [
            (b'Transfer-Encoding', b'chunked')
        ],
        'body': b'hello world'
    },
    'CHUNKED_W_TRAILING_HEADERS': {
        'name': "chunked with trailing headers. blech.",
        'type': ParserType.request,
        'raw': (
            b'POST /chunked_w_trailing_headers HTTP/1.1\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'5\r\nhello\r\n'
            b'6\r\n world\r\n'
            b'0\r\n'
            b'Vary: *\r\n'
            b'Content-Type: text/plain\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': None,
        'fragment': None,
        'request_path': b'/chunked_w_trailing_headers',
        'request_url': b'/chunked_w_trailing_headers',
        'num_headers': 3,
        'headers': [
            (b'Transfer-Encoding',  b'chunked'),
            (b'Vary', b'*'),
            (b'Content-Type', b'text/plain')
        ],
        'body': b'hello world'
    },
    'CHUNKED_W_BULLSHIT_AFTER_LENGTH': {
        'name': "with bullshit after the length",
        'type': ParserType.request,
        'raw': (
            b'POST /chunked_w_bullshit_after_length HTTP/1.1\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'5; ihatew3;whatthefuck=aretheseparametersfor\r\nhello\r\n'
            b'6; blahblah; blah\r\n world\r\n'
            b'0\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': None,
        'fragment': None,
        'request_path': b'/chunked_w_bullshit_after_length',
        'request_url': b'/chunked_w_bullshit_after_length',
        'num_headers': 1,
        'headers': [
            (b'Transfer-Encoding', b'chunked')
        ],
        'body': b'hello world'
    },
    'WITH_QUOTES': {
        'name': "with quotes",
        'type': ParserType.request,
        'raw': b'GET /with_"stupid"_quotes?foo="bar" HTTP/1.1\r\n\r\n',
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': b'foo="bar"',
        'fragment': None,
        'request_path': b'/with_"stupid"_quotes',
        'request_url': b'/with_"stupid"_quotes?foo="bar"',
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'APACHEBENCH_GET': {
        'name ': "apachebench get",
        'type': ParserType.request,
        'raw': (
            b'GET /test HTTP/1.0\r\n'
            b'Host: 0.0.0.0:5000\r\n'
            b'User-Agent: ApacheBench/2.3\r\n'
            b'Accept: */*\r\n\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 0,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/test',
        'request_url': b'/test',
        'num_headers': 3,
        'headers': [
            (b'Host', b'0.0.0.0:5000'),
            (b'User-Agent', b'ApacheBench/2.3'),
            (b'Accept', b'*/*')
        ],
        'body': b''
    },
    'QUERY_URL_WITH_QUESTION_MARK_GET': {
        'name ': "query url with question mark",
        'type': ParserType.request,
        'raw': b'GET /test.cgi?foo=bar?baz HTTP/1.1\r\n\r\n',
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': b'foo=bar?baz',
        'fragment': None,
        'request_path': b'/test.cgi',
        'request_url': b'/test.cgi?foo=bar?baz',
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'PREFIX_NEWLINE_GET': {
        'name ': "newline prefix get",
        'type': ParserType.request,
        'raw': b'\r\nGET /test HTTP/1.1\r\n\r\n',
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/test',
        'request_url': b'/test',
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'UPGRADE_REQUEST': {
        'name ': "upgrade request",
        'type': ParserType.request,
        'raw': (
            b'GET /demo HTTP/1.1\r\n'
            b'Host: example.com\r\n'
            b'Connection: Upgrade\r\n'
            b'Sec-WebSocket-Key2: 12998 5 Y3 1  .P00\r\n'
            b'Sec-WebSocket-Protocol: sample\r\n'
            b'Upgrade: WebSocket\r\n'
            b'Sec-WebSocket-Key1: 4 @1  46546xW%0l 1 5\r\n'
            b'Origin: http://example.com\r\n'
            b'\r\n'
            b'Hot diggity dogg'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/demo',
        'request_url': b'/demo',
        'num_headers': 7,
        'upgrade': b'Hot diggity dogg',
        'headers': [
            (b'Host', b'example.com'),
            (b'Connection', b'Upgrade'),
            (b'Sec-WebSocket-Key2', b'12998 5 Y3 1  .P00'),
            (b'Sec-WebSocket-Protocol', b'sample'),
            (b'Upgrade', b'WebSocket'),
            (b'Sec-WebSocket-Key1', b'4 @1  46546xW%0l 1 5'),
            (b'Origin', b'http://example.com')
        ],
        'body': b''
    },
    'CONNECT_REQUEST': {
        'name ': "connect request",
        'type': ParserType.request,
        'raw': (
            b'CONNECT 0-home0.netscape.com:443 HTTP/1.0\r\n'
            b'User-agent: Mozilla/1.1N\r\n'
            b'Proxy-authorization: basic aGVsbG86d29ybGQ=\r\n'
            b'\r\n'
            b'some data\r\n'
            b'and yet even more data'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 0,
        'method': Method.connect,
        'query_string': None,
        'fragment': None,
        'request_path': None,
        'request_url': b'0-home0.netscape.com:443',
        'num_headers': 2,
        'upgrade': b'some data\r\nand yet even more data',
        'headers': [
            (b'User-agent', b'Mozilla/1.1N'),
            (b'Proxy-authorization', b'basic aGVsbG86d29ybGQ=')
        ],
        'body': b''
    },
    'REPORT_REQ': {
        'name': "report request",
        'type': ParserType.request,
        'raw': (
            b'REPORT /test HTTP/1.1\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.report,
        'query_string': None,
        'fragment': None,
        'request_path': b'/test',
        'request_url': b'/test',
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'NO_HTTP_VERSION': {
        'name': "request with no http version",
        'type': ParserType.request,
        'raw': (
            b'GET /\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 0,
        'http_minor': 9,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/',
        'request_url': b'/',
        'num_headers': 0,
        'headers': {},
        'body': b''
    },
    'MSEARCH_REQ': {
        'name': "m-search request",
        'type': ParserType.request,
        'raw': (
            b'M-SEARCH * HTTP/1.1\r\n'
            b'HOST: 239.255.255.250:1900\r\n'
            b'MAN: \"ssdp:discover\"\r\n'
            b'ST: \"ssdp:all\"\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.msearch,
        'query_string': None,
        'fragment': None,
        'request_path': b'*',
        'request_url': b'*',
        'num_headers': 3,
        'headers': [
            (b'HOST', b'239.255.255.250:1900'),
            (b'MAN', b'"ssdp:discover"'),
            (b'ST', b'"ssdp:all"')
        ],
        'body': b''
    },
    'LINE_FOLDING_IN_HEADER': {
        'name': "line folding in header value",
        'type': ParserType.request,
        'raw': (
            b'GET / HTTP/1.1\r\n'
            b'Line1:   abc\r\n'
            b'\tdef\r\n'
            b' ghi\r\n'
            b'\t\tjkl\r\n'
            b'  mno \r\n'
            b'\t \tqrs\r\n'
            b'Line2: \t line2\t\r\n'
            b'Line3:\r\n'
            b' line3\r\n'
            b'Line4: \r\n'
            b' \r\n'
            b'Connection:\r\n'
            b' close\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/',
        'request_url': b'/',
        'num_headers': 5,
        'headers': [
            (b'Line1', b'abc\tdef ghi\t\tjkl  mno \t \tqrs'),
            (b'Line2', b'line2\t'),
            (b'Line3', b'line3'),
            (b'Line4', b''),
            (b'Connection', b'close'),
        ],
        'body': b''
    },
    'QUERY_TERMINATED_HOST': {
        'name': "host terminated by a query string",
        'type': ParserType.request,
        'raw': (
            b'GET http://hypnotoad.org?hail=all HTTP/1.1\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': b'hail=all',
        'fragment': None,
        'request_path': None,
        'request_url': b'http://hypnotoad.org?hail=all',
        'host': b'hypnotoad.org',
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'QUERY_TERMINATED_HOSTPORT': {
        'name': "host:port terminated by a query string",
        'type': ParserType.request,
        'raw': (
            b'GET http://hypnotoad.org:1234?hail=all HTTP/1.1\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': b'hail=all',
        'fragment': None,
        'request_path': None,
        'request_url': b'http://hypnotoad.org:1234?hail=all',
        'host': b'hypnotoad.org',
        'port': 1234,
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'SPACE_TERMINATED_HOSTPORT': {
        'name': "host:port terminated by a space",
        'type': ParserType.request,
        'raw': (
            b'GET http://hypnotoad.org:1234 HTTP/1.1\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': None,
        'request_url': b'http://hypnotoad.org:1234',
        'host': b'hypnotoad.org',
        'port': 1234,
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'PATCH_REQ': {
        'name ': "PATCH request",
        'type': ParserType.request,
        'raw': (
            b'PATCH /file.txt HTTP/1.1\r\n'
            b'Host: www.example.com\r\n'
            b'Content-Type: application/example\r\n'
            b'If-Match: \"e0023aa4e\"\r\n'
            b'Content-Length: 10\r\n'
            b'\r\n'
            b'cccccccccc'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.patch,
        'query_string': None,
        'fragment': None,
        'request_path': b'/file.txt',
        'request_url': b'/file.txt',
        'num_headers': 4,
        'headers': [
            (b'Host', b'www.example.com'),
            (b'Content-Type', b'application/example'),
            (b'If-Match', b'"e0023aa4e"'),
            (b'Content-Length', b'10')
        ],
        'body': b'cccccccccc'
    },
    'CONNECT_CAPS_REQUEST': {
        'name ': "connect caps request",
        'type': ParserType.request,
        'raw': (
            b'CONNECT HOME0.NETSCAPE.COM:443 HTTP/1.0\r\n'
            b'User-agent: Mozilla/1.1N\r\n'
            b'Proxy-authorization: basic aGVsbG86d29ybGQ=\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 0,
        'method': Method.connect,
        'query_string': None,
        'fragment': None,
        'request_path': None,
        'request_url': b'HOME0.NETSCAPE.COM:443',
        'num_headers': 2,
        'upgrade': b'',
        'headers': [
            (b'User-agent', b'Mozilla/1.1N'),
            (b'Proxy-authorization', b'basic aGVsbG86d29ybGQ=')
        ],
        'body': b''
    },
    'EAT_TRAILING_CRLF_NO_CONNECTION_CLOSE': {
        'name ': "eat CRLF between requests, no \"Connection: close\" header",
        'type': ParserType.request,
        'raw': (
            b'POST / HTTP/1.1\r\n'
            b'Host: www.example.com\r\n'
            b'Content-Type: application/x-www-form-urlencoded\r\n'
            b'Content-Length: 4\r\n'
            b'\r\n'
            b'q=42\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': None,
        'fragment': None,
        'request_path': b'/',
        'request_url': b'/',
        'num_headers': 3,
        'headers': [
            (b'Host', b'www.example.com'),
            (b'Content-Type', b'application/x-www-form-urlencoded'),
            (b'Content-Length', b'4')
        ],
        'body': b'q=42'
    },
    'EAT_TRAILING_CRLF_WITH_CONNECTION_CLOSE': {
        'name ': "eat CRLF between requests even if \"Connection: close\" is set",
        'type': ParserType.request,
        'raw': (
            b'POST / HTTP/1.1\r\n'
            b'Host: www.example.com\r\n'
            b'Content-Type: application/x-www-form-urlencoded\r\n'
            b'Content-Length: 4\r\n'
            b'Connection: close\r\n'
            b'\r\n'
            b'q=42\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.post,
        'query_string': None,
        'fragment': None,
        'request_path': b'/',
        'request_url': b'/',
        'num_headers': 4,
        'headers': [
            (b'Host', b'www.example.com'),
            (b'Content-Type', b'application/x-www-form-urlencoded'),
            (b'Content-Length', b'4'),
            (b'Connection', b'close')
        ],
        'body': b'q=42'
    },
    'PURGE_REQ': {
        'name ': "PURGE request",
        'type': ParserType.request,
        'raw': (
            b'PURGE /file.txt HTTP/1.1\r\n'
            b'Host: www.example.com\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.purge,
        'query_string': None,
        'fragment': None,
        'request_path': b'/file.txt',
        'request_url': b'/file.txt',
        'num_headers': 1,
        'headers': [(b'Host', b'www.example.com')],
        'body': b''
    },
    'SEARCH_REQ': {
        'name ': "SEARCH request",
        'type': ParserType.request,
        'raw': (
            b'SEARCH / HTTP/1.1\r\n'
            b'Host: www.example.com\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.search,
        'query_string': None,
        'fragment': None,
        'request_path': b'/',
        'request_url': b'/',
        'num_headers': 1,
        'headers': [(b'Host', b'www.example.com')],
        'body': b''
    },
    'PROXY_WITH_BASIC_AUTH': {
        'name': "host:port and basic_auth",
        'type': ParserType.request,
        'raw': (
            b'GET http://a%12:b!&*$@hypnotoad.org:1234/toto HTTP/1.1\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'fragment': None,
        'request_path': b'/toto',
        'request_url': b'http://a%12:b!&*$@hypnotoad.org:1234/toto',
        'host': b'hypnotoad.org',
        'userinfo': b'a%12:b!&*$',
        'query_string': None,
        'port': 1234,
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'LINE_FOLDING_IN_HEADER_WITH_LF': {
        'name': "line folding in header value",
        'type': ParserType.request,
        'raw': (
            b'GET / HTTP/1.1\n'
            b'Line1:   abc\n'
            b'\tdef\n'
            b' ghi\n'
            b'\t\tjkl\n'
            b'  mno \n'
            b'\t \tqrs\n'
            b'Line2: \t line2\t\n'
            b'Line3:\n'
            b' line3\n'
            b'Line4: \n'
            b' \n'
            b'Connection:\n'
            b' close\n'
            b'\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'method': Method.get,
        'query_string': None,
        'fragment': None,
        'request_path': b'/',
        'request_url': b'/',
        'num_headers': 5,
        'headers': [
            (b'Line1', b'abc\tdef ghi\t\tjkl  mno \t \tqrs'),
            (b'Line2', b'line2\t'),
            (b'Line3', b'line3'),
            (b'Line4', b''),
            (b'Connection', b'close')
        ],
        'body': b''
    }
}


RESPONSES = {
    'GOOGLE_301': {
        'name': "google 301",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 301 Moved Permanently\r\n'
            b'Location: http://www.google.com/\r\n'
            b'Content-Type: text/html; charset=UTF-8\r\n'
            b'Date: Sun, 26 Apr 2009 11:11:49 GMT\r\n'
            b'Expires: Tue, 26 May 2009 11:11:49 GMT\r\n'
            b'X-$PrototypeBI-Version: 1.6.0.3\r\n'
            b'Cache-Control: public, max-age=2592000\r\n'
            b'Server: gws\r\n'
            b'Content-Length:  219  \r\n'
            b'\r\n'
            b'<HTML><HEAD><meta http-equiv=\"content-type\" content=\"text/html;charset=utf-8\">\n'
            b'<TITLE>301 Moved</TITLE></HEAD><BODY>\n'
            b'<H1>301 Moved</H1>\n'
            b'The document has moved\n'
            b'<A HREF=\"http://www.google.com/\">here</A>.\r\n'
            b'</BODY></HTML>\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 301,
        'response_status': b'Moved Permanently',
        'num_headers': 8,
        'headers': [
            (b'Location', b'http://www.google.com/'),
            (b'Content-Type', b'text/html; charset=UTF-8'),
            (b'Date', b'Sun, 26 Apr 2009 11:11:49 GMT'),
            (b'Expires', b'Tue, 26 May 2009 11:11:49 GMT'),
            (b'X-$PrototypeBI-Version', b'1.6.0.3'),
            (b'Cache-Control', b'public, max-age=2592000'),
            (b'Server', b'gws'),
            (b'Content-Length', b'219  ')
        ],
        'body': (
            b'<HTML><HEAD><meta http-equiv=\"content-type\" content=\"text/html;charset=utf-8\">\n'
            b'<TITLE>301 Moved</TITLE></HEAD><BODY>\n'
            b'<H1>301 Moved</H1>\n'
            b'The document has moved\n'
            b'<A HREF=\"http://www.google.com/\">here</A>.\r\n'
            b'</BODY></HTML>\r\n'
        )
    },
    'NO_CONTENT_LENGTH_RESPONSE': {
        'name': "no content-length response",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Date: Tue, 04 Aug 2009 07:59:32 GMT\r\n'
            b'Server: Apache\r\n'
            b'X-Powered-By: Servlet/2.5 JSP/2.1\r\n'
            b'Content-Type: text/xml; charset=utf-8\r\n'
            b'Connection: close\r\n'
            b'\r\n'
            b'<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n'
            b'<SOAP-ENV:Envelope xmlns:SOAP-ENV=\"http://schemas.xmlsoap.org/soap/envelope/\">\n'
            b'  <SOAP-ENV:Body>\n'
            b'    <SOAP-ENV:Fault>\n'
            b'       <faultcode>SOAP-ENV:Client</faultcode>\n'
            b'       <faultstring>Client Error</faultstring>\n'
            b'    </SOAP-ENV:Fault>\n'
            b'  </SOAP-ENV:Body>\n'
            b'</SOAP-ENV:Envelope>'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 5,
        'headers': [
            (b'Date', b'Tue, 04 Aug 2009 07:59:32 GMT'),
            (b'Server', b'Apache'),
            (b'X-Powered-By', b'Servlet/2.5 JSP/2.1'),
            (b'Content-Type', b'text/xml; charset=utf-8'),
            (b'Connection', b'close')
        ],
        'body': (
            b'<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n'
            b'<SOAP-ENV:Envelope xmlns:SOAP-ENV=\"http://schemas.xmlsoap.org/soap/envelope/\">\n'
            b'  <SOAP-ENV:Body>\n'
            b'    <SOAP-ENV:Fault>\n'
            b'       <faultcode>SOAP-ENV:Client</faultcode>\n'
            b'       <faultstring>Client Error</faultstring>\n'
            b'    </SOAP-ENV:Fault>\n'
            b'  </SOAP-ENV:Body>\n'
            b'</SOAP-ENV:Envelope>'
        )
    },
    'NO_HEADERS_NO_BODY_404': {
        'name': "404 no headers no body",
        'type': ParserType.response,
        'raw': b'HTTP/1.1 404 Not Found\r\n\r\n',
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 404,
        'response_status': b'Not Found',
        'num_headers': 0,
        'headers': [],
        'body_size': 0,
        'body': b'',
    },
    'NO_REASON_PHRASE': {
        'name': "301 no response phrase",
        'type': ParserType.response,
        'raw': b'HTTP/1.1 301\r\n\r\n',
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 301,
        'response_status': b'',
        'num_headers': 0,
        'headers': [],
        'body': b'',
    },
    'TRAILING_SPACE_ON_CHUNKED_BODY': {
        'name':"200 trailing space on chunked body",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Content-Type: text/plain\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'25  \r\n'
            b'This is the data in the first chunk\r\n'
            b'\r\n'
            b'1C\r\n'
            b'and this is the second one\r\n'
            b'\r\n'
            b'0  \r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 2,
        'headers': [
            (b'Content-Type', b'text/plain'),
            (b'Transfer-Encoding', b'chunked')
        ],
        'body_size': 37+28,
        'body': (
            b'This is the data in the first chunk\r\n'
            b'and this is the second one\r\n'
        )
    },
    'NO_CARRIAGE_RET': {
        'name': "no carriage ret",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\n'
            b'Content-Type: text/html; charset=utf-8\n'
            b'Connection: close\n'
            b'\n'
            b'these headers are from http://news.ycombinator.com/'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 2,
        'headers': [
            (b'Content-Type', b'text/html; charset=utf-8'),
            (b'Connection', b'close')
        ],
        'body': b'these headers are from http://news.ycombinator.com/'
    },
    'PROXY_CONNECTION': {
        'name':"proxy connection",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Content-Type: text/html; charset=UTF-8\r\n'
            b'Content-Length: 11\r\n'
            b'Proxy-Connection: close\r\n'
            b'Date: Thu, 31 Dec 2009 20:55:48 +0000\r\n'
            b'\r\n'
            b'hello world'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 4,
        'headers': [
            (b'Content-Type', b'text/html; charset=UTF-8'),
            (b'Content-Length', b'11'),
            (b'Proxy-Connection', b'close'),
            (b'Date', b'Thu, 31 Dec 2009 20:55:48 +0000')
        ],
        'body': b'hello world'
    },
    'UNDERSTORE_HEADER_KEY': {
        'name':"underscore header key",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Server: DCLK-AdSvr\r\n'
            b'Content-Type: text/xml\r\n'
            b'Content-Length: 0\r\n'
            b'DCLK_imp: v7;x;114750856;0-0;0;17820020;0/0;21603567/21621457/1;;~okv=;dcmt=text/xml;;~cs=o\r\n\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 4,
        'headers': [
            (b'Server', b'DCLK-AdSvr'),
            (b'Content-Type', b'text/xml'),
            (b'Content-Length', b'0'),
            (b'DCLK_imp', b'v7;x;114750856;0-0;0;17820020;0/0;21603567/21621457/1;;~okv=;dcmt=text/xml;;~cs=o')
        ],
        'body': b'',
    },
    'BONJOUR_MADAME_FR': {
        'name': "bonjourmadame.fr",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.0 301 Moved Permanently\r\n'
            b'Date: Thu, 03 Jun 2010 09:56:32 GMT\r\n'
            b'Server: Apache/2.2.3 (Red Hat)\r\n'
            b'Cache-Control: public\r\n'
            b'Pragma: \r\n'
            b'Location: http://www.bonjourmadame.fr/\r\n'
            b'Vary: Accept-Encoding\r\n'
            b'Content-Length: 0\r\n'
            b'Content-Type: text/html; charset=UTF-8\r\n'
            b'Connection: keep-alive\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 0,
        'status_code': 301,
        'response_status': b'Moved Permanently',
        'num_headers': 9,
        'headers': [
            (b'Date', b'Thu, 03 Jun 2010 09:56:32 GMT'),
            (b'Server', b'Apache/2.2.3 (Red Hat)'),
            (b'Cache-Control', b'public'),
            (b'Pragma', b''),
            (b'Location', b'http://www.bonjourmadame.fr/'),
            (b'Vary',  b'Accept-Encoding'),
            (b'Content-Length', b'0'),
            (b'Content-Type', b'text/html; charset=UTF-8'),
            (b'Connection', b'keep-alive')
        ],
        'body': b'',
    },
    'RES_FIELD_UNDERSCORE': {
        'name': "field underscore",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Date: Tue, 28 Sep 2010 01:14:13 GMT\r\n'
            b'Server: Apache\r\n'
            b'Cache-Control: no-cache, must-revalidate\r\n'
            b'Expires: Mon, 26 Jul 1997 05:00:00 GMT\r\n'
            b'.et-Cookie: PlaxoCS=1274804622353690521; path=/; domain=.plaxo.com\r\n'
            b'Vary: Accept-Encoding\r\n'
            b'_eep-Alive: timeout=45\r\n'
            b'_onnection: Keep-Alive\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'Content-Type: text/html\r\n'
            b'Connection: close\r\n'
            b'\r\n'
            b'0\r\n\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 11,
        'headers': [
            (b'Date', b'Tue, 28 Sep 2010 01:14:13 GMT'),
            (b'Server', b'Apache'),
            (b'Cache-Control', b'no-cache, must-revalidate'),
            (b'Expires', b'Mon, 26 Jul 1997 05:00:00 GMT'),
            (b'.et-Cookie', b'PlaxoCS=1274804622353690521; path=/; domain=.plaxo.com'),
            (b'Vary', b'Accept-Encoding'),
            (b'_eep-Alive', b'timeout=45'),
            (b'_onnection', b'Keep-Alive'),
            (b'Transfer-Encoding', b'chunked'),
            (b'Content-Type', b'text/html'),
            (b'Connection', b'close')
        ],
        'body': b''
    },
    'NON_ASCII_IN_STATUS_LINE': {
        'name': "non-ASCII in status line",
        'type': ParserType.response,
        'raw': (
            u'HTTP/1.1 500 Oriëntatieprobleem\r\n'
            u'Date: Fri, 5 Nov 2010 23:07:12 GMT+2\r\n'
            u'Content-Length: 0\r\n'
            u'Connection: close\r\n'
            u'\r\n'
        ).encode('utf-8'),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 500,
        'response_status': u'Oriëntatieprobleem'.encode('utf-8'),
        'num_headers': 3,
        'headers': [
            (b'Date', b'Fri, 5 Nov 2010 23:07:12 GMT+2'),
            (b'Content-Length', b'0'),
            (b'Connection', b'close')
        ],
        'body': b''
    },
    'HTTP_VERSION_0_9': {
        'name': "http version 0.9",
        'type': ParserType.response,
        'raw': (
            b'HTTP/0.9 200 OK\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 0,
        'http_minor': 9,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 0,
        'headers': [],
        'body': b''
    },
    'NO_CONTENT_LENGTH_NO_TRANSFER_ENCODING_RESPONSE': {
        'name': "neither content-length nor transfer-encoding response",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Content-Type: text/plain\r\n'
            b'\r\n'
            b'hello world'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 1,
        'headers': [
            (b'Content-Type', b'text/plain')
        ],
        'body': b'hello world'
    },
    'NO_BODY_HTTP10_KA_200': {
        'name': "HTTP/1.0 with keep-alive and EOF-terminated 200 status",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.0 200 OK\r\n'
            b'Connection: keep-alive\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 0,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 1,
        'headers': [
            (b'Connection', b'keep-alive')
        ],
        'body_size': 0,
        'body': b''
    },
    'NO_BODY_HTTP10_KA_204': {
        'name': "HTTP/1.0 with keep-alive and a 204 status",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.0 204 No content\r\n'
            b'Connection: keep-alive\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 0,
        'status_code': 204,
        'response_status': b'No content',
        'num_headers': 1,
        'headers': [
            (b'Connection', b'keep-alive')
        ],
        'body_size': 0,
        'body': b''
    },
    'NO_BODY_HTTP11_KA_200': {
        'name': "HTTP/1.1 with an EOF-terminated 200 status",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 0,
        'headers': [],
        'body_size': 0,
        'body': b''
    },
    'NO_BODY_HTTP11_KA_204': {
        'name': "HTTP/1.1 with a 204 status",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 204 No content\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 204,
        'response_status': b'No content',
        'num_headers': 0,
        'headers': [],
        'body_size': 0,
        'body': b''
    },
    'NO_BODY_HTTP11_NOKA_204': {
        'name': "HTTP/1.1 with a 204 status and keep-alive disabled",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 204 No content\r\n'
            b'Connection: close\r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 204,
        'response_status': b'No content',
        'num_headers': 1,
        'headers': [
            (b'Connection', b'close')
        ],
        'body_size': 0,
        'body': b''
    },
    'NO_BODY_HTTP11_KA_CHUNKED_200': {
        'name': "HTTP/1.1 with chunked endocing and a 200 response",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 OK\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'0\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'OK',
        'num_headers': 1,
        'headers': [
            (b'Transfer-Encoding', b'chunked')
        ],
        'body_size': 0,
        'body': b''
    },
    'AMAZON_COM': {
        'name': "amazon.com",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 301 MovedPermanently\r\n'
            b'Date: Wed, 15 May 2013 17:06:33 GMT\r\n'
            b'Server: Server\r\n'
            b'x-amz-id-1: 0GPHKXSJQ826RK7GZEB2\r\n'
            b'p3p: policyref=\"http://www.amazon.com/w3c/p3p.xml\",CP=\"CAO DSP LAW CUR ADM IVAo IVDo CONo OTPo OUR DELi PUBi OTRi BUS PHY ONL UNI PUR FIN COM NAV INT DEM CNT STA HEA PRE LOC GOV OTC \"\r\n'
            b'x-amz-id-2: STN69VZxIFSz9YJLbz1GDbxpbjG6Qjmmq5E3DxRhOUw+Et0p4hr7c/Q8qNcx4oAD\r\n'
            b'Location: http://www.amazon.com/Dan-Brown/e/B000AP9DSU/ref=s9_pop_gw_al1?_encoding=UTF8&refinementId=618073011&pf_rd_m=ATVPDKIKX0DER&pf_rd_s=center-2&pf_rd_r=0SHYY5BZXN3KR20BNFAY&pf_rd_t=101&pf_rd_p=1263340922&pf_rd_i=507846\r\n'
            b'Vary: Accept-Encoding,User-Agent\r\n'
            b'Content-Type: text/html; charset=ISO-8859-1\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
            b'1\r\n'
            b'\n\r\n'
            b'0\r\n'
            b'\r\n'
        ),
        'should_keep_alive': True,
        'message_complete_on_eof': False,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 301,
        'response_status': b'MovedPermanently',
        'num_headers': 9,
        'headers': [
            (b'Date', b'Wed, 15 May 2013 17:06:33 GMT'),
            (b'Server', b'Server'),
            (b'x-amz-id-1', b'0GPHKXSJQ826RK7GZEB2'),
            (b'p3p', b'policyref="http://www.amazon.com/w3c/p3p.xml",CP="CAO DSP LAW CUR ADM IVAo IVDo CONo OTPo OUR DELi PUBi OTRi BUS PHY ONL UNI PUR FIN COM NAV INT DEM CNT STA HEA PRE LOC GOV OTC "'),
            (b'x-amz-id-2', b'STN69VZxIFSz9YJLbz1GDbxpbjG6Qjmmq5E3DxRhOUw+Et0p4hr7c/Q8qNcx4oAD'),
            (b'Location', b'http://www.amazon.com/Dan-Brown/e/B000AP9DSU/ref=s9_pop_gw_al1?_encoding=UTF8&refinementId=618073011&pf_rd_m=ATVPDKIKX0DER&pf_rd_s=center-2&pf_rd_r=0SHYY5BZXN3KR20BNFAY&pf_rd_t=101&pf_rd_p=1263340922&pf_rd_i=507846'),
            (b'Vary', b'Accept-Encoding,User-Agent'),
            (b'Content-Type', b'text/html; charset=ISO-8859-1'),
            (b'Transfer-Encoding', b'chunked')
        ],
        'body': b'\n'
    },
    'EMPTY_REASON_PHRASE_AFTER_SPACE': {
        'name': "empty reason phrase after space",
        'type': ParserType.response,
        'raw': (
            b'HTTP/1.1 200 \r\n'
            b'\r\n'
        ),
        'should_keep_alive': False,
        'message_complete_on_eof': True,
        'http_major': 1,
        'http_minor': 1,
        'status_code': 200,
        'response_status': b'',
        'num_headers': 0,
        'headers': [],
        'body': b''
    }
}


MESSAGES = []
MESSAGES.extend(REQUESTS.values())
MESSAGES.extend(RESPONSES.values())


@pytest.fixture(params=MESSAGES)
def message(request):
    return request.param


@pytest.fixture(params=list(ParserType))
def parser_type(request):
    return request.param


def test_version():
    assert isinstance(__version__, str)
    assert isinstance(__version_info__, tuple)
    assert len(__version_info__) == 3


def test_http_parser_version():
    assert isinstance(__http_parser_version__, str)
    assert isinstance(__http_parser_version_info__, tuple)
    assert len(__http_parser_version_info__) == 3


class TestMethod(object):
    @pytest.fixture(params=list(Method))
    def method(self, request):
        return request.param

    def test_str(self, method):
        if method == Method.msearch:
            assert str(method) == 'M-SEARCH'
        else:
            assert str(method) == method.name.upper()

    def test_bytes(self, method):
        if method is Method.msearch:
            assert bytes(method) == b'M-SEARCH'
        else:
            assert bytes(method) == method.name.upper().encode('ascii')

    def test_repr(self, method):
        assert str(method) in repr(method)


class TestErrno(object):
    @pytest.fixture(params=list(Errno))
    def errno(self, request):
        return request.param

    def test_c_name(self, errno):
        assert errno.c_name.startswith('HPE')

    def test_description(self, errno):
        assert isinstance(errno.description, str)


class TestingHTTPParser(HTTPParser):
    def __init__(self, *args, **kwargs):
        super(TestingHTTPParser, self).__init__(*args, **kwargs)
        self.messages = []
        self.completed_messages = 0
        self.currently_parsing_eof = False

    def execute(self, data):
        self.currently_parsing_eof = len(data) == 0
        return super(TestingHTTPParser, self).execute(data)

    def on_message_begin(self):
        self.messages.append({
            'message_begin_cb_called': True
        })

    def on_url(self, data):
        if 'request_url' in self.messages[-1]:
            self.messages[-1]['request_url'] += data
        else:
            self.messages[-1]['request_url'] = data

    def on_status(self, data):
        if 'response_status' in self.messages[-1]:
            self.messages[-1]['response_status'] += data
        else:
            self.messages[-1]['response_status'] = data

    def on_header_field(self, data):
        self.messages[-1].setdefault('headers', [(bytearray(), bytearray())])
        if self.messages[-1].get('last_header_element', 'field') != 'field':
            self.messages[-1]['headers'].append((bytearray(), bytearray()))

        self.messages[-1]['headers'][-1][0].extend(data)
        self.messages[-1]['last_header_element'] = 'field'

    def on_header_value(self, data):
        self.messages[-1]['headers'][-1][1].extend(data)
        self.messages[-1]['last_header_element'] = 'value'

    def on_headers_complete(self):
        message = self.messages[-1]
        message.setdefault('headers', [])
        for i, (key, value) in enumerate(message['headers']):
            message['headers'][i] = bytes(key), bytes(value)
        message['method'] = self.method
        message['status_code'] = self.status_code
        message['http_major'] = self.http_major
        message['http_minor'] = self.http_minor
        message['headers_complete_cb_called'] = True
        message['should_keep_alive'] = self.should_keep_alive()

    def on_body(self, data):
        if 'body' in self.messages[-1]:
            self.messages[-1]['body'] += data
            self.messages[-1]['body_size'] += len(data)
        else:
            self.messages[-1]['body'] = data
            self.messages[-1]['body_size'] = len(data)
        self.check_body_is_final()

    def check_body_is_final(self):
        assert not self.messages[-1].get('body_is_final', False)
        self.messages[-1]['body_is_final'] = self.body_is_final()

    def on_message_complete(self):
        self.completed_messages += 1
        assert self.messages[-1]['should_keep_alive'] == self.should_keep_alive()
        if 'body' in self.messages[-1] and self.body_is_final():
            assert self.messages[-1]['body_is_final']
        self.messages[-1]['message_complete_cb_called'] = True
        self.messages[-1]['message_complete_on_eof'] = self.currently_parsing_eof


def count_parsed_messages(messages):
    result = 0
    for message in messages:
        result += 1
        if 'upgrade' in message:
            break
    return result


def assert_message_equal(generated, expected):
    assert generated['http_major'] == expected['http_major']
    assert generated['http_minor'] == expected['http_minor']
    if expected['type'] is ParserType.request:
        assert generated['method'] == expected['method']
        assert generated['request_url'] == expected['request_url']
        if generated['method'] is not Method.connect:
            url = parse_url(generated['request_url'], is_connect=False)
            if 'host' in expected:
                assert url.host == expected['host']
            if 'userinfo' in expected:
                assert url.userinfo == expected['userinfo']
            if 'port' in expected:
                assert int(url.port.decode('ascii')) == expected['port']
            assert url.path == expected['request_path']
            assert url.query == expected['query_string']
            assert url.fragment == expected['fragment']
    else:
        assert generated['status_code'] == expected['status_code']
        assert generated.get('response_status', b'') == expected['response_status']
    assert generated['should_keep_alive'] == expected['should_keep_alive']
    assert generated['message_complete_on_eof'] == expected['message_complete_on_eof']
    assert generated['message_begin_cb_called']
    assert generated['headers_complete_cb_called']
    assert generated['message_complete_cb_called']
    if 'body_size' in expected:
        assert generated.get('body_size', 0) == expected['body_size']
    else:
        assert generated.get('body', b'') == expected['body']

    assert len(generated.get('headers', [])) == expected['num_headers']
    if expected['num_headers']:
        for gen_header, exp_header in zip(generated['headers'], expected['headers']):
            assert gen_header[0] == exp_header[0]
            assert gen_header[1] == exp_header[1]


class TestHTTPParser(object):
    @pytest.fixture(params=[
        'on_message_begin',
        'on_url',
        'on_status',
        'on_header_field',
        'on_header_value',
        'on_headers_complete',
        'on_body',
        'on_message_complete'
    ])
    def callback_name(self, request):
        return request.param

    def test_header_overflow_error(self, parser_type):
        parser = HTTPParser(parser_type)

        if parser_type is ParserType.request:
            data = b'GET / HTTP/1.1\r\n'
        else:
            data = b'HTTP/1.0 200 OK\r\n'
        parser.execute(data)

        with pytest.raises(HTTPParserError) as exc_info:
            data = b'header-key: header-value\r\n'
            for _ in range(10000):
                parser.execute(data)
        assert 'header_overflow' in str(exc_info)

    @pytest.mark.parametrize('length', [1000, 100000])
    def test_no_overflow_long_body(self, parser_type, length):
        parser = HTTPParser(parser_type)

        if parser_type is ParserType.request:
            first_line = b'POST / HTTP/1.0'
        else:
            first_line = b'HTTP/1.0 200 OK'
        headers = b'\r\n'.join([
            first_line,
            b'Connection: Keep-Alive',
            'Content-Length: {}'.format(length).encode('ascii'),
        ]) + b'\r\n\r\n'
        parser.execute(headers)

        # this should not fail with an exception
        for _ in range(length):
            parser.execute(b'a')

    @pytest.mark.parametrize(('length', 'should_fail'), [
        (2 ** 64 // 10 - 1, False),
        (2 ** 64 - 1, True),
        (2 ** 64, True)
    ])
    def test_header_content_length_overflow_error(self, length, should_fail):
        message = ('\r\n'.join([
            'HTTP/1.1 200 OK',
            'Content-Length: {}'.format(length),
        ]) + '\r\n').encode('ascii')
        parser = HTTPParser(ParserType.response)
        if should_fail:
            with pytest.raises(HTTPParserError) as exc_info:
                parser.execute(message)
            assert 'invalid_content_length' in str(exc_info)
        else:
            parser.execute(message)

    @pytest.mark.parametrize(('length', 'should_fail'), [
        (2 ** 64 // 16 - 1, False),
        (2 ** 64 - 1, True),
        (2 ** 64, True)
    ])
    def test_chunk_content_length_overflow_error(self, length, should_fail):
        message = '\r\n'.join([
            'HTTP/1.1 200 OK',
            'Transfer-Encoding: chunked',
            '',
            '{:x}'.format(length),
            '...'
        ]).encode('ascii')
        parser = HTTPParser(ParserType.response)
        if should_fail:
            with pytest.raises(HTTPParserError) as exc_info:
                parser.execute(message)
            assert 'invalid_content_length' in str(exc_info)
        else:
            parser.execute(message)

    def test_message(self, message):
        for i in range(len(message['raw'])):
            parser = TestingHTTPParser(message['type'])
            first_part = message['raw'][:i]
            second_part = message['raw'][i:]
            for part in [first_part, second_part]:
                try:
                    parser.execute(part)
                except ConnectionUpgrade as upgrade:
                    break
            try:
                parser.execute(b'')
            except ConnectionUpgrade:
                pass

            assert parser.completed_messages == 1
            assert_message_equal(parser.messages[0], message)

    def test_message_pause(self, message):
        class PausingHTTPParser(TestingHTTPParser):
            def on_message_begin(self):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_message_begin()

            def on_url(self, data):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_url(data)

            def on_status(self, data):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_status(data)

            def on_header_field(self, data):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_header_field(data)

            def on_header_value(self, data):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_header_value(data)

            def on_headers_complete(self):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_headers_complete()

            def on_body(self, data):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_body(data)

            def on_message_complete(self):
                assert not self.pause
                self.pause = True
                return super(PausingHTTPParser, self).on_message_complete()

        parser = PausingHTTPParser(message['type'])
        offset = 0
        while message['raw'][offset:]:
            try:
                read = parser.execute(message['raw'][offset:])
            except ConnectionUpgrade as upgrade:
                if (
                    parser.messages[-1].get('message_complete_cb_called') and
                    message.get('upgrade')
                ):
                    break
                offset += upgrade.offset
            except HTTPParserError as error:
                assert error.errno is Errno.paused
                assert error.offset > 0
                offset += error.offset
            else:
                assert read >= len(message['raw'][offset:])
                offset += read
            parser.pause = False
        try:
            parser.execute(b'')
        except ConnectionUpgrade as upgrade:
            pass
        assert parser.completed_messages == 1
        assert_message_equal(parser.messages[0], message)

    @pytest.mark.parametrize(('first', 'second', 'third'),
        list(zip(
            (
                request for request in REQUESTS.values()
                if request.get('should_keep_alive', True)
            ),
            (
                request for request in REQUESTS.values()
                if request.get('should_keep_alive', True)
            ),
            REQUESTS.values()
        )) +
        list(zip(
            (
                response for response in RESPONSES.values()
                if response.get('should_keep_alive', True)
            ),
            (
                response for response in RESPONSES.values()
                if response.get('should_keep_alive', True)
            ),
            RESPONSES.values()
        ))
    )
    def test_multiple3(self, first, second, third):
        messages = [first, second, third]
        parser = TestingHTTPParser(first['type'])
        total = first['raw'] + second['raw'] + third['raw']
        try:
            parser.execute(total)
        except ConnectionUpgrade as upgrade:
            pass
        else:
            parser.execute(b'')
        assert parser.completed_messages == count_parsed_messages(messages)
        for generated, expected in zip(parser.messages, messages):
            assert_message_equal(generated, expected)

    @pytest.mark.parametrize('countable_message', [
        RESPONSES['NO_HEADERS_NO_BODY_404'],
        RESPONSES['TRAILING_SPACE_ON_CHUNKED_BODY'],
        # TODO: message large chunk
    ])
    def test_message_count_body(self, countable_message):
        class CountingHTTPParser(TestingHTTPParser):
            def on_body(self, data):
                if 'body_size' in self.messages[-1]:
                    self.messages[-1]['body_size'] += len(data)
                else:
                    self.messages[-1]['body_size'] = len(data)
                self.check_body_is_final()
        parser = CountingHTTPParser(countable_message['type'])
        offset = 0
        while offset < len(countable_message['raw']):
            toread = min(len(countable_message['raw']) - offset, 4024)
            parser.execute(countable_message['raw'][offset:toread])
            offset += 4024
        parser.execute(b'')
        assert parser.completed_messages == 1
        assert_message_equal(parser.messages[0], countable_message)

    @pytest.mark.parametrize('messages', [
        (
            REQUESTS['GET_NO_HEADERS_NO_BODY'],
            REQUESTS['GET_ONE_HEADER_NO_BODY'],
            REQUESTS['GET_NO_HEADERS_NO_BODY']
        ),
        (
            REQUESTS['POST_CHUNKED_ALL_YOUR_BASE'],
            REQUESTS['POST_IDENTITY_BODY_WORLD'],
            REQUESTS['GET_FUNKY_CONTENT_LENGTH']
        ),
        (
            REQUESTS['TWO_CHUNKS_MULT_ZERO_END'],
            REQUESTS['CHUNKED_W_TRAILING_HEADERS'],
            REQUESTS['CHUNKED_W_BULLSHIT_AFTER_LENGTH']
        ),
        (
            REQUESTS['QUERY_URL_WITH_QUESTION_MARK_GET'],
            REQUESTS['PREFIX_NEWLINE_GET'],
            REQUESTS['CONNECT_REQUEST']
        )
    ])
    def test_scan(self, messages):
        total_raw = b''.join(message['raw'] for message in messages)
        for j in range(2, len(total_raw)):
            for i in range(1, j):
                parser = TestingHTTPParser(messages[0]['type'])

                first = total_raw[:i]
                second = total_raw[i:j]
                third = total_raw[j:]
                assert first + second + third == total_raw
                for part in [first, second, third]:
                    try:
                        parser.execute(part)
                    except ConnectionUpgrade as upgrade:
                        break
                assert parser.completed_messages == len(messages)
                for generated, expected in zip(parser.messages, messages):
                    assert_message_equal(generated, expected)

    def test_callback_exception_is_reraised(self, callback_name):
        if callback_name == 'on_status':
            parser_type = ParserType.response
        else:
            parser_type = ParserType.request

        if parser_type is ParserType.request:
            first_line = 'POST / HTTP/1.0'
        else:
            first_line = 'HTTP/1.0 200 OK'
        message = '\r\n'.join([
            first_line,
            'Content-Length: 6',
            '',
            'foobar'
        ]).encode('ascii')

        def callback(self, *args, **kwargs):
            raise ValueError('an exception occurred')

        parser_cls = type('HTTPParserTest', (HTTPParser, ), {
            callback_name: callback
        })
        parser = parser_cls(parser_type)
        with pytest.raises(ValueError) as exc_info:
            parser.execute(message)
        assert 'an exception occurred' in str(exc_info)

    def test_callback_returns_invalid_value(self, callback_name):
        if callback_name == 'on_status':
            parser_type = ParserType.response
        else:
            parser_type = ParserType.request

        if parser_type is ParserType.request:
            first_line = 'POST / HTTP/1.0'
        else:
            first_line = 'HTTP/1.0 200 OK'
        message = '\r\n'.join([
            first_line,
            'Content-Length: 6',
            '',
            'foobar'
        ]).encode('ascii')

        def callback(self, *args, **kwargs):
            return 'this is bad'

        parser_cls = type('HTTPParserTest', (HTTPParser, ), {
            callback_name: callback
        })
        parser = parser_cls(parser_type)
        with pytest.raises(TypeError):
            parser.execute(message)


@pytest.mark.parametrize(('data', 'is_connect', 'is_url', 'result'), [
    (b'http://hostname/', False, True, {
        'schema': b'http',
        'host': b'hostname',
        'path': b'/'
    }),
    (b'http://hostname:444/', False, True, {
        'schema': b'http',
        'host': b'hostname',
        'port': b'444',
        'path': b'/'
    }),
    (b'hostname:443', True, True, {
        'host': b'hostname',
        'port': b'443'
    }),
    (b'http://[1:2::3:4]:67/', False, True, {
        'schema': b'http',
        'host': b'1:2::3:4',
        'port': b'67',
        'path': b'/'
    }),
    (b'[1:2::3:4]:443', True, True, {
        'host': b'1:2::3:4',
        'port': b'443'
    }),
    (b'http://[2001:0000:0000:0000:0000:0000:1.9.1.1]/', False, True, {
        'schema': b'http',
        'host': b'2001:0000:0000:0000:0000:0000:1.9.1.1',
        'path': b'/'
    }),
    (b'http://a.tbcdn.cn/p/fp/2010c/??fp-header-min.css,fp-base-min.css,fp-channel-min.css,fp-product-min.css,fp-mall-min.css,fp-category-min.css,fp-sub-min.css,fp-gdp4p-min.css,fp-css3-min.css,fp-misc-min.css?t=20101022.css', False, True, {
        'schema': b'http',
        'host': b'a.tbcdn.cn',
        'path': b'/p/fp/2010c/',
        'query': b'?fp-header-min.css,fp-base-min.css,fp-channel-min.css,fp-product-min.css,fp-mall-min.css,fp-category-min.css,fp-sub-min.css,fp-gdp4p-min.css,fp-css3-min.css,fp-misc-min.css?t=20101022.css'
    }),
    (b'/toto.html?toto=a%20b', False, True, {
        'path': b'/toto.html',
        'query': b'toto=a%20b'
    }),
    (b'/toto.html#titi', False, True, {
        'path': b'/toto.html',
        'fragment': b'titi'
    }),
    (b'http://www.webmasterworld.com/r.cgi?f=21&d=8405&url=http://www.example.com/index.html?foo=bar&hello=world#midpage', False, True, {
        'schema': b'http',
        'host': b'www.webmasterworld.com',
        'path': b'/r.cgi',
        'query': b'f=21&d=8405&url=http://www.example.com/index.html?foo=bar&hello=world',
        'fragment': b'midpage'
    }),
    (b'http://host.com:8080/p/a/t/h?query=string#hash', False, True, {
        'schema': b'http',
        'host': b'host.com',
        'port': b'8080',
        'path': b'/p/a/t/h',
        'query': b'query=string',
        'fragment': b'hash'
    }),
    (b'http://a:b@host.com:8080/p/a/t/h?query=string#hash', False, True, {
        'schema': b'http',
        'userinfo': b'a:b',
        'host': b'host.com',
        'port': b'8080',
        'path': b'/p/a/t/h',
        'query': b'query=string',
        'fragment': b'hash'
    }),
    (b'http://a:b@@hostname:443/', False, False, {}),
    (b'http://:443/', False, False, {}),
    (b'http://hostname:/', False, False, {}),
    (b'a:b@hostname:443', True, False, {}),
    (b':433', True, False, {}),
    (b'hostname:', True, False, {}),
    (b'hostname:443/', True, False, {}),
    (b'/foo bar', False, False, {}),
    (b'http://a%20:b@host.com/', False, True, {
        'schema': b'http',
        'userinfo': b'a%20:b',
        'host': b'host.com',
        'path': b'/'
    }),
    (b'/foo\rbar/', False, False, {}),
    (b'http://hostname::443/', False, False, {}),
    (b'http://a::b@host.com/', False, True, {
        'schema': b'http',
        'userinfo': b'a::b',
        'host': b'host.com',
        'path': b'/'
    }),
    (b'/foo\nbar/', False, False, {}),
    (b'http://@hostname/fo', False, True, {
        'schema': b'http',
        'host': b'hostname',
        'path': b'/fo'
    }),
    (b'http://host\name/fo', False, False, {}),
    (b'http://host%name/fo', False, False, {}),
    (b'http://host;name/fo', False, False, {}),
    (b'http://a!;-_!=+$@host.com/', False, True, {
        'schema': b'http',
        'userinfo': b'a!;-_!=+$',
        'host': b'host.com',
        'path': b'/'
    }),
    (b'http://@/fo', False, False, {}),
    (b'http://toto@/fo', False, False, {}),
    (b'http:///fo', False, False, {}),
    (b'http://host=ame/fo', False, False, {}),
    (b'/foo\tbar/', False, False, {}),
    (b'/foo\fbar/', False, False, {}),
])
def test_parse_url(data, is_connect, is_url, result):
    if is_url:
        url = parse_url(data, is_connect)
        expected = dict.fromkeys(url._fields)
        expected.update(result)
        assert url == URL(**expected)
    else:
        with pytest.raises(ValueError):
            parse_url(data, is_connect)
