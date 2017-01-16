from forest.routers import Router

r = Router()


@r('path', 'name')
def test_ok(request):
    print(request)
    return request


import re
if __name__ == '__main__':
    # test_ok('request')
    path = "/articles/{category}/{id:[0-9]+}"
    re_str = r'\{(.*?)\}'
    r = re.compile(re_str)
    res = r.findall(path)
    print(res)
