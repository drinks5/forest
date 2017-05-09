# coding: utf-8
"""
    httpparser._bindings
    ~~~~~~~~~~~~~~~~~~~~

    The C definitions are based on the `http_parser.h` file of the http-parser
    library.

    :copyright: 2014 by Daniel Neuhäuser
    :license: BSD, see LICENSE.rst for details
"""
import os
import cffi


ffi = cffi.FFI()
ffi.cdef("""
typedef struct http_parser http_parser;
typedef struct http_parser_settings http_parser_settings;


/* Callbacks should return non-zero to indicate an error. The parser will
 * then halt execution.
 *
 * The one exception is on_headers_complete. In a HTTP_RESPONSE parser
 * returning '1' from on_headers_complete will tell the parser that it
 * should not expect a body. This is used when receiving a response to a
 * HEAD request which may contain 'Content-Length' or 'Transfer-Encoding:
 * chunked' headers that indicate the presence of a body.
 *
 * http_data_cb does not return data chunks. It will be call arbitrarally
 * many times for each string. E.G. you might get 10 callbacks for "on_url"
 * each providing just a few characters more data.
 */
typedef int (*http_data_cb) (http_parser*, const char *at, size_t length);
typedef int (*http_cb) (http_parser*);


/* Request Methods */
enum http_method
  { HTTP_DELETE = 0
  , HTTP_GET = 1
  , HTTP_HEAD = 2
  , HTTP_POST = 3
  , HTTP_PUT = 4
  /* pathological */
  , HTTP_CONNECT = 5
  , HTTP_OPTIONS = 6
  , HTTP_TRACE = 7
  /* webdav */
  , HTTP_COPY = 8
  , HTTP_LOCK = 9
  , HTTP_MKCOL = 10
  , HTTP_MOVE = 11
  , HTTP_PROPFIND = 12
  , HTTP_PROPPATCH = 13
  , HTTP_SEARCH = 14
  , HTTP_UNLOCK = 15
  /* subversion */
  , HTTP_REPORT = 16
  , HTTP_MKACTIVITY = 17
  , HTTP_CHECKOUT = 18
  , HTTP_MERGE = 19
  /* upnp */
  , HTTP_MSEARCH = 20
  , HTTP_NOTIFY = 21
  , HTTP_SUBSCRIBE = 22
  , HTTP_UNSUBSCRIBE = 23
  /* RFC-5789 */
  , HTTP_PATCH = 24
  , HTTP_PURGE = 25
  };


enum http_parser_type { HTTP_REQUEST, HTTP_RESPONSE, HTTP_BOTH };


/* Flag values for http_parser.flags field */
enum flags
  { F_CHUNKED               = 1  /* 1 << 0 */
  , F_CONNECTION_KEEP_ALIVE = 2  /* 1 << 1 */
  , F_CONNECTION_CLOSE      = 4  /* 1 << 2 */
  , F_TRAILING              = 8  /* 1 << 3 */
  , F_UPGRADE               = 16 /* 1 << 4 */
  , F_SKIPBODY              = 32 /* 1 << 5 */
  };


enum http_errno
  { HPE_OK

  /* Callback-related errors */
  , HPE_CB_message_begin
  , HPE_CB_url
  , HPE_CB_header_field
  , HPE_CB_header_value
  , HPE_CB_headers_complete
  , HPE_CB_body
  , HPE_CB_message_complete
  , HPE_CB_status

  /* Parsing-related errors */
  , HPE_INVALID_EOF_STATE
  , HPE_HEADER_OVERFLOW
  , HPE_CLOSED_CONNECTION
  , HPE_INVALID_VERSION
  , HPE_INVALID_STATUS
  , HPE_INVALID_METHOD
  , HPE_INVALID_URL
  , HPE_INVALID_HOST
  , HPE_INVALID_PORT
  , HPE_INVALID_PATH
  , HPE_INVALID_QUERY_STRING
  , HPE_INVALID_FRAGMENT
  , HPE_LF_EXPECTED
  , HPE_INVALID_HEADER_TOKEN
  , HPE_INVALID_CONTENT_LENGTH
  , HPE_INVALID_CHUNK_SIZE
  , HPE_INVALID_CONSTANT
  , HPE_INVALID_INTERNAL_STATE
  , HPE_STRICT
  , HPE_PAUSED
  , HPE_UNKNOWN
  };


struct http_parser {
  /** PRIVATE **/
  unsigned int type : 2;         /* enum http_parser_type */
  unsigned int flags : 6;        /* F_* values from 'flags' enum; semi-public */
  unsigned int state : 8;        /* enum state from http_parser.c */
  unsigned int header_state : 8; /* enum header_state from http_parser.c */
  unsigned int index : 8;        /* index into current matcher */

  uint32_t nread;          /* # bytes read in various scenarios */
  uint64_t content_length; /* # bytes in body (0 if no Content-Length header) */

  /** READ-ONLY **/
  unsigned short http_major;
  unsigned short http_minor;
  unsigned int status_code : 16; /* responses only */
  unsigned int method : 8;       /* requests only */
  unsigned int http_errno : 7;

  /* 1 = Upgrade header was present and the parser has exited because of that.
   * 0 = No upgrade header present.
   * Should be checked when http_parser_execute() returns in addition to
   * error checking.
   */
  unsigned int upgrade : 1;

  /** PUBLIC **/
  void *data; /* A pointer to get hook to the "connection" or "socket" object */
};


struct http_parser_settings {
  http_cb      on_message_begin;
  http_data_cb on_url;
  http_data_cb on_status;
  http_data_cb on_header_field;
  http_data_cb on_header_value;
  http_cb      on_headers_complete;
  http_data_cb on_body;
  http_cb      on_message_complete;
};


enum http_parser_url_fields
  { UF_SCHEMA           = 0
  , UF_HOST             = 1
  , UF_PORT             = 2
  , UF_PATH             = 3
  , UF_QUERY            = 4
  , UF_FRAGMENT         = 5
  , UF_USERINFO         = 6
  , UF_MAX              = 7
  };


/* Result structure for http_parser_parse_url().
 *
 * Callers should index into field_data[] with UF_* values iff field_set
 * has the relevant (1 << UF_*) bit set. As a courtesy to clients (and
 * because we probably have padding left over), we convert any port to
 * a uint16_t.
 */
struct http_parser_url {
  uint16_t field_set;           /* Bitmask of (1 << UF_*) values */
  uint16_t port;                /* Converted UF_PORT string */

  struct {
    uint16_t off;               /* Offset into buffer in which field starts */
    uint16_t len;               /* Length of run in buffer */
  } field_data[7]; /* UF_MAX */
};


/* Returns the library version. Bits 16-23 contain the major version number,
 * bits 8-15 the minor version number and bits 0-7 the patch level.
 * Usage example:
 *
 *   unsigned long version = http_parser_version();
 *   unsigned major = (version >> 16) & 255;
 *   unsigned minor = (version >> 8) & 255;
 *   unsigned patch = version & 255;
 *   printf("http_parser v%u.%u.%u\n", major, minor, version);
 */
unsigned long http_parser_version(void);

void http_parser_init(http_parser *parser, enum http_parser_type type);


size_t http_parser_execute(http_parser *parser,
                           const http_parser_settings *settings,
                           const char *data,
                           size_t len);


/* If http_should_keep_alive() in the on_headers_complete or
 * on_message_complete callback returns 0, then this should be
 * the last message on the connection.
 * If you are the server, respond with the "Connection: close" header.
 * If you are the client, close the connection.
 */
int http_should_keep_alive(const http_parser *parser);

/* Returns a string version of the HTTP method. */
const char *http_method_str(enum http_method m);

/* Return a string name of the given error */
const char *http_errno_name(enum http_errno err);

/* Return a string description of the given error */
const char *http_errno_description(enum http_errno err);

/* Parse a URL; return nonzero on failure */
int http_parser_parse_url(const char *buf, size_t buflen,
                          int is_connect,
                          struct http_parser_url *u);

/* Pause or un-pause the parser; a nonzero value pauses */
void http_parser_pause(http_parser *parser, int paused);

/* Checks if this is the final chunk of the body. */
int http_body_is_final(const http_parser *parser);
""")
lib = ffi.dlopen(os.path.join(os.path.dirname(__file__), '_http_parser.so'))
