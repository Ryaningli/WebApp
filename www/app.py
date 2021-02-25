import asyncio
from aiohttp import web
from Log import MyLog

logger = MyLog.get_log()
log = logger.get_logger()


async def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html', charset='utf-8')


async def init():
    app = web.Application()
    app.router.add_get('/', index)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 9000)
    await site.start()
    log.info('服务启动')
    return site


loop = asyncio.get_event_loop()
loop.run_until_complete(init())
loop.run_forever()
