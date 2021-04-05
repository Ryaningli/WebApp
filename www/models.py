import time
import uuid
from orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField


def next_id():
    # uuid.uuid4()可以生成一个随机的uuid，目的是为了区分不同事务
    # hex可以把自身返回为一个16进制整数，所以这个函数就是生成各种id，里面还包含时间
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


# 获取当前格式化的时间
def get_time():
    time_local = time.localtime(time.time())
    return time.strftime('%Y-%m-%d %H:%M:%S', time_local)


class User(Model):
    __table__ = 'users'
    id = StringField(primary_key=True, default=next_id(), ddl='varchar(50)')
    phone = StringField(ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    create_time = StringField(default=get_time())


class Blog(Model):
    __table__ = 'blogs'
    id = IntegerField(primary_key=True, default=None)
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    create_time = StringField(default=get_time())
    update_time = StringField(default=get_time())


class Comment(Model):
    __table__ = 'comments'
    id = IntegerField(primary_key=True, default=None)
    blog_id = IntegerField()
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    create_time = StringField(default=get_time())