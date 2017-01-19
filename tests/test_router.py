from forest.routers import Router

r = Router()


@r('path', 'name')
def test_ok(request):
    print(request)
    return request


def braceIndices(string):
    level, idx, idxs = 0, 0, []
    for i, s in enumerate(string):
        if s == '{':
            level += 1
            if level == 1:
                idx = i
        elif s == '}':
            level -= 1
            if level == 0:
                idxs.extend([idx, i + 1])
            elif level < 0:
                raise ValueError("unbalanced braces in %s" % s)
    return idxs


import re
if __name__ == '__main__':
    # test_ok('request')
    path = "/articles/{category}/{id:[0-9]+}"
    re_str = r'\{(.*?)\}'
    r = re.compile(re_str)
    res = r.findall(path)
    print(res)
    braceIndices(path)
