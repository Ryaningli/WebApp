import asyncio
import aiomysql
from www.Log import MyLog

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


def create_args_string(num):
    L = []
    # 若报错，将n改成单下划线
    for n in range(num):
        L.append('?')
        return ', '.join(L)


class ModeMetaclass(type):
    """
    __new__()放法接收到的参数依次是：
    cls：当前准备创建的类的对象 class
    name：类的名字 str
    bases：类继承的父类集合 Tuple
    attrs：类的方法集合
    """
    def __new__(cls, name, bases, attrs):
        # 排除Model类本身，返回它自己
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        # 获取table名称
        tableName = attrs.get('__table__', None) or name
        log.info('找到model: %s (table: %s)' % (name, tableName))

        # 获取所有Field(字段)和主键名
        mappings = dict()
        fields = []
        primaryKey = None

        for k, v in attrs.items():
            if isinstance(v, Field):
                log.info('找到mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field(字段主键重复)')
                    primaryKey = k
                else:
                    fields.append(k)

        if not primaryKey:
            raise RuntimeError('Primary key not found(找不到主键).')

        for k in mappings.keys():
            attrs.pop(k)

        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings    # 保存属性和列的映射关系
        attrs['__table__'] = tableName      # table名
        attrs['__primary_key__'] = primaryKey   # 主键属性名
        attrs['__field__'] = fields     # 除主键外的属性名
        attrs['__select__'] = 'SELECT `%s`, %s FROM `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'INSERT INTO `%s` (%s, `%s) VALUES (%s)' % (
            tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'UPDATE `%s` SET %s WHERE `%s`=?' % (
            tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'DELETE FROM `%s` WHERE `%s`=?' % (tableName, primaryKey)
