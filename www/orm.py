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
        # host=kw.get('host', 'localhost'),
        host=kw.get('host', '47.110.74.149'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
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


class ModelMetaclass(type):
    """
    __new__()放法接收到的参数依次是：
    cls：当前准备创建的类的对象 class
    name：类的名字 str
    bases：类继承的父类集合 Tuple
    attrs：类的方法集合
    """
    def __new__(mcs, name, bases, attrs):
        # 排除Model类本身，返回它自己
        if name == 'Model':
            return type.__new__(mcs, name, bases, attrs)

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
        attrs['__fields__'] = fields     # 除主键外的属性名
        attrs['__select__'] = 'SELECT `%s`, %s FROM `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'INSERT INTO `%s` (%s, `%s`) VALUES (%s)' % (
            tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'UPDATE `%s` SET %s WHERE `%s`=?' % (
            tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'DELETE FROM `%s` WHERE `%s`=?' % (tableName, primaryKey)
        return type.__new__(mcs, name, bases, attrs)


# metaclass参数提示Model要通过上面的__new__来创建
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    # 返回参数为key的自身属性；让self['__fields__]可以写为self.__field__
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    # 设置自身属性
    def __setattr__(self, key, value):
        self[key] = value

    # 通过属性返回想要的值
    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            # 如果value是None，定位某个键：value不为None就直接返回
            field = self.__mappings__[key]
            if field.default is not None:
                # 如果field.default不是None， 就把它赋值给value
                value = field.default() if callable(field.default) else field.default
                log.debug('使用默认值 %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    # 往Model类添加class方法，就可以让所有子类调用class方法
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        sql = [cls.__select__]

        if where:
            # where 默认值为None
            # 如果where有值就在sql加上字符串'where' 和变量where
            sql.append('WHERE')
            sql.append(where)

        if args is None:
            # args默认值为None
            # 如果findAll函数未传入有效的where参数，则将'[]'传入args
            args = []

        orderBy = kw.get('orderBy', None)
        if orderBy:
            # orderBy有值时给sql加上它，为空时啥都不干
            sql.append('ORDER BY')
            sql.append(orderBy)

        # 开头和orderBy类似
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('LIMIT')
            if isinstance(limit, int):
                sql.append('?')
                sql.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value(无效的范围值): %s' % str(limit))

        rs = await select(' '.join(sql), args)

        # 返回选择的列表里的所有值，完成findAll函数
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        sql = ['SELECT %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('WHERE')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            # 如果rs内无元素，返回None，有元素返回某个数
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        # 通过主键找对象
        rs = await select('%s WHERE `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    # 往Model类添加实例方法，就可以让所有子类调用实例方法
    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            log.warning('failed to remove by primary key: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        print(rows)
        if rows != 1:
            log.warning('failed to remove by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            log.warning('failed to remove by primary key: affected rows: %s' % rows)


# 定义Field
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 定义Field子类及其子类的默认值
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)
