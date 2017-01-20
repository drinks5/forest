cdef class Request:
    cdef:
        bytes body
        str path
        object headers
        str version
        str method
        str query_string
        str parsed_json
