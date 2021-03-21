import hashlib
import json
import re
import time
from aiohttp import web
import markdown
from coroweb import get, post
from models import User, Comment, Blog, next_id
from apis import APIValueError, APIError, APIPermissionError, Page
from config import configs
from log import log

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret


def user2cookie(user, max_age):
    expires = str(int(time.time()) + max_age)
    s = '%s-%s-%s-%s' % (user.id, user.password, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.password, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            log.info('无效sha1')
            return None
        user.password = '******'
        return user
    except Exception as e:
        log.exception(e)
        return None


# 获取页码信息
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


# 检查用户是否是管理员
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError(message='非管理员账户')


'''前端页面'''


# 前端首页
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


# 前端注册页面
@get('/register')
def register():
    return {
        '__template__': 'register.html'
    }


# 前端登录页面
@get('/login')
def login():
    return {
        '__template__': 'login.html'
    }


# 日志详情
@get('/blog/{id}')
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = markdown.markdown(c.content)
    blog.html_content = markdown.markdown(blog.content)
    return{
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


'''管理端页面'''


# 编辑/创建日志页面
@get('/manage/blog/create')
def manage_blog_create():
    return {
        '__template__': 'manage_blog_edit.html',
        'id': '',
        'action': '/api/blog'
    }


# 管理端日志列表页面
@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }


'''接口'''


# 获取所有用户接口
@get('/api/users')
async def api_get_users():
    users = await User.findAll(orderBy='created_at desc')
    for u in users:
        u.password = '******'
    return dict(users=users)


_RE_PHONE = re.compile(r'^1[3|4|5|7|8][0-9]{9}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


# 注册接口
@post('/api/register')
async def api_register(*, phone, name, password):
    if not name or not name.strip():
        raise APIValueError('name', '用户名无效')
    if not phone or not _RE_PHONE.match(phone):
        raise APIValueError('phone', '手机号无效')
    if not password or not _RE_SHA1.match(password):
        raise APIValueError('password', '密码不合法')
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


# 登录接口
@post('/api/login')
async def api_login(*, phone, password):
    if not phone:
        raise APIValueError('phone', '手机号无效')
    if not password:
        raise APIValueError('password', '密码无效')
    users = await User.findAll('phone=?', [phone])
    if len(users) == 0:
        raise APIValueError('phone', '手机号未注册')
    user = users[0]

    # 检查密码
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(password.encode('utf-8'))
    if user.password != sha1.hexdigest():
        raise APIValueError('password', '密码错误')

    # 验证成功，设置cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)

    user.password = '******'
    user.created_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(user.created_at)))    # 创建日期转正常格式
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


# 创建bolg接口
@post('/api/blog')
async def api_blog_create(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', '标题不能为空')
    if not summary or not summary.strip():
        raise APIValueError('summary', '摘要不能为空')
    if not content or not content.strip():
        raise APIValueError('content', '内容不能为空')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image,
                name=name.strip(), summary=summary.strip(), content=content.strip())
    await blog.save()
    blog.created_at = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(blog.created_at)))    # 创建日期转正常格式
    # 提交日志后查询当前日志并返回id（后期可分开）
    b = await Blog.find_sql('SELECT MAX(id) FROM blogs;')
    blog.id = b['MAX(id)']
    return blog


# 获取日志列表接口
@get('/api/blog')
async def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = await Blog.findAll(orderBy='created_at DESC', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)
