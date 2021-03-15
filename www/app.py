import asyncio
from datetime import datetime
import json
import os
import time
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from log import log, logger
import orm
from coroweb import add_routes, add_static
from config import configs
from handlers import COOKIE_NAME, cookie2user


def init_jinja2(app, **kw):
    log.info('初始化jinja2...')
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    log.info('设置jinja2模板路径: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


async def logger_factory(app, handler):
    async def logger(request):
        log.info('Request: %s %s' % (request.method, request.path))
        return (await handler(request))
    return logger


# 认证处理工厂--把当前用户绑定到request上，并对URL/manage进行拦截，检查当前用户是否为管理员身份
async def auth_factory(app, handler):
    async def auth(request):
        log.info('检查用户: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                log.info('设置当前用户: %s' % user.phone)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/login')
        return (await handler(request))
    return auth


# 数据处理工厂
async def data_factory(app, handler):
    async def parse_data(request):
        if request.content_type.startswith('application/json'):
            request.__data__ = await request.json()
            log.info('请求json: %s' % str(request.__data__))
        elif request.content_type.startswith('application/x-www-form-urlencoded'):
            request.__data__ = await request.post()
            log.info('请求来自: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data


# 响应返回处理工厂
async def response_factory(app, handler):
    async def response(request):
        log.info('Response handler...')
        r = await handler(request)
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return '1分钟前'
    if delta < 3600:
        return '%s分钟前' % (delta // 60)
    if delta < 86400:
        return '%s小时前' % (delta // 3600)
    if delta < 604800:
        return '%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return '%s年%s月%s日' % (dt.year, dt.month, dt.day)


async def init():
    await orm.create_pool(loop=loop, host=configs.db.host, port=configs.db.port, user=configs.db.user,
                          password=configs.db.password, db=configs.db.database)
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, response_factory
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)

    runner = web.AppRunner(app)
    await runner.setup()
    # 这里ip使用0.0.0.0，使用127.0.0.1的话外部网络无法访问
    site = web.TCPSite(runner, '0.0.0.0', 9000)
    await site.start()
    log.info('服务启动: http://0.0.0.0:9000...')
    return site

loop = asyncio.get_event_loop()


def run():
    loop.run_until_complete(init())
    loop.run_forever()


if __name__ == '__main__':
    run()