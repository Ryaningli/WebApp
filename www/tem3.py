import hashlib
import time


_COOKIE_KEY = 'adsfa'


def u(max_age):
    expires = str(int(time.time()) + max_age)
    s = '%s-%s-%s-%s' % ('00161459408349667f2db3c638d47bdaa033b30b62a87c3000', 'abc123', expires, _COOKIE_KEY)
    L = ['00161459408349667f2db3c638d47bdaa033b30b62a87c3000', expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

print(u(86000))