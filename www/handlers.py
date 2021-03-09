import hashlib
import json
import re
import time
from aiohttp import web
from coroweb import get, post
from models import User, Comment, Blog, next_id
from apis import APIValueError, APIError
from config import configs


COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    expires = str(int(time.time()) + max_age)
    s = '%s-%s-%s-%s' % (user.id, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


@get('/')
def index(request):
    summary = '这是博客的内容最好，多几个字，因为都很长的。'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }


@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy='created_at desc')
    for u in users:
        u.password = '******'
    return dict(users=users)


# 前端注册页面
@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }


_RE_PHONE = re.compile(r'1[3|4|5|7|8][0-9]{9}')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


# 注册接口
@post('/api/users')
async def api_register_user(*, phone, name, password):
    if not name or name.strip():
        raise APIValueError('name')
    if not phone or not _RE_PHONE.match(phone):
        raise APIValueError('phone')
    if not password or not _RE_SHA1.match(password):
        raise APIValueError('password')
    users = await User.findAll('phone=?', [phone])
    if len(users) > 0:
        raise APIError('register: failed', 'phone', '手机号已注册')
    uid = next_id()
    sha1_password = '%s:%s' % (uid, password)
    user = User(id=uid, name=name.strip(), phone=phone,
                password=hashlib.sha1(sha1_password.encode('utf-8')).hexdigest(),
                image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(phone.encode('utf-8')).hexdigest())
    await user.save()

    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.password = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r