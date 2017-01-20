import logging


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def time(f):
    def inner(*args, **kwargs):
        from time import time
        s = time()
        res = f(*args, **kwargs)
        e = time()
        print('time elapsed: %s' % (e - s))
        return res
    return inner
