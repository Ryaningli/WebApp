import asyncio
from www import orm
from www.models import User

loop = asyncio.get_event_loop()


async def test():
    await orm.create_pool(user='ryan', password='1116', db='awesome', loop=loop)

    u = User(name='Ryan', phone='18815596963', email='166997125002@qq.com', password='abc123', image='about:blank')

    await u.save()


async def se():
    await orm.create_pool(user='ryan', password='1116', db='awesome', loop=loop)
    u = User()
    a = await u.find('001614495926582b4285af46b0c48ada736283e39a4efb6000')
    return print(a)


async def de():
    await orm.create_pool(user='ryan', password='1116', db='awesome', loop=loop)
    u = User(id='0016144991756592c3e816e576b4255a56cdd15c6d1f465000')
    await u.remove()

loop.run_until_complete(test())
