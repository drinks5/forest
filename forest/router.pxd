cdef class RouteMatch:
    cdef:
        object handler
        tuple vars


cdef class Router:
    cdef:
        Router parent
        list routes
        bint strictSlash

cdef class RouteRegexpGroup:
    cdef:
        str host
        str path
        str queries

cdef class Route:
    cdef:
        Router parent
        bint strictSlash
        list matchers
        object handler
        RouteRegexpGroup regexp


# sth wrong happend
# cdef class RouteRegexp:
#     cdef:
#         object pattern
#         str template
#         object reverse
#         bint strictSlash
