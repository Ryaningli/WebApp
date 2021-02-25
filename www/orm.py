import asyncio
import aiomysql
from Log import MyLog

logger = MyLog.get_log()
log = logger.get_logger()


def log_sql(sql, args=()):
    log.info('SQL语句: %s' % sql)


async def create_pool(loop, **kw):
    log.info('创建数据库连接池')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf-8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


async def select(sql, args, size=None):
    log_sql(sql, args)
    global __pool
    with (await __pool) as conn:
        # 创建游标
        cur = await conn.cursor(aiomysql.DictCursor)
        await cur.execute(sql.replace('?', '%s'), args or ())

        if size:
            # 获取行数为size的多行查询结果集， 返回一个列表
            rs = await cur.fetchmany(size)
        else:
            # 获取查询结果的所有行，返回一个列表
            rs = await cur.fetchall()

        # 关闭游标
        await cur.close()

        log.info('返回行数: %s' % len(rs))
        return rs


# 执行INSERT、UPDATE、DELETE语句
async def execute(sql, args):
    log_sql(sql)
    global __pool
    with (await __pool) as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?', '%s'), args)
            # 获取影响的行数
            affected = cur.rowcount
            await cur.close()
        # 此处若报错，将e改成单下划线
        except BaseException as e:
            raise
        return affected
