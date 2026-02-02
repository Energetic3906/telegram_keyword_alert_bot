#coding=utf-8
import os
import re
from pathlib import Path
from peewee import (
    SqliteDatabase, Model, IntegerField, CharField, 
    SmallIntegerField, DateTimeField, BigIntegerField,
    OperationalError
)
from playhouse.migrate import SqliteMigrator, migrate

__all__ = [
    'db',
    'User',
    'User_subscribe_list',
    'User_block_list',
]

# 1. 获取当前文件所在目录的上一级目录的上一级 (即项目根目录)
BASE_DIR = Path(__file__).resolve().parent.parent
ETC_DIR = BASE_DIR / 'etc'
DB_PATH = ETC_DIR / 'my_database.db'

# 2. 自动创建目录 (防止首次运行报错)
if not ETC_DIR.exists():
    ETC_DIR.mkdir(parents=True, exist_ok=True)

# 3. 初始化数据库连接
# pragmas={'journal_mode': 'wal'}: 开启 WAL 模式，大幅提升并发读写性能，减少锁表
# check_same_thread=False: 允许在不同线程/协程中使用同一个连接对象 (对 Telethon 这种异步库很重要)
_connect = SqliteDatabase(str(DB_PATH), pragmas={'journal_mode': 'wal'}, check_same_thread=False)

class _Base(Model):
    class Meta:
        database = _connect

class User(_Base):
    """用户数据表"""
    # Telegram ID 是 64 位整数，推荐使用 BigIntegerField
    chat_id = BigIntegerField(index=True, unique=True)
    create_time = DateTimeField('%Y-%m-%d %H:%M:%S', index=True)

class User_subscribe_list(_Base):
    """用户订阅表"""
    user_id = IntegerField(index=True)
    channel_name = CharField(50, null=False) # 频道名称
    
    # 存储频道/群组 ID
    chat_id = CharField(50, null=False, default='') 
    
    keywords = CharField(120, null=False)
    status = SmallIntegerField(default=0) # 0 正常 1删除
    create_time = DateTimeField('%Y-%m-%d %H:%M:%S', null=True)

class User_block_list(_Base):
    """用户屏蔽列表（黑名单设置）"""
    user_id = IntegerField(index=True)
    
    blacklist_type = CharField(50, null=False) # length_limit, keyword, username
    blacklist_value = CharField(120, null=False)

    channel_name = CharField(50, null=True, default='')
    chat_id = CharField(50, null=True, default='') 
    
    create_time = DateTimeField('%Y-%m-%d %H:%M:%S', null=True)
    update_time = DateTimeField('%Y-%m-%d %H:%M:%S', null=True)

    class Meta:
        # 联合索引示例，根据需要取消注释
        # indexes = (
        #     (('user_id', 'channel_name', 'chat_id'), False), 
        # )
        pass

class _Db:
    def __init__(self):
        self.connect = _connect
        # 显式连接（可选，Peewee 会自动处理，但手动连接方便排查错误）
        if self.connect.is_closed():
            self.connect.connect()

        self.models = [
            User,
            User_subscribe_list,
            User_block_list,
        ]
        
        self.initialize_tables()

    def initialize_tables(self):
        """初始化表结构并检查字段缺失（自动迁移）"""
        # 创建不存在的表
        self.connect.create_tables(self.models, safe=True)

        # 检查并添加缺失的字段
        migrator = SqliteMigrator(self.connect)
        
        for model_class in self.models:
            # 绑定模型属性到 db 实例，保持原有调用习惯 (utils.db.user)
            setattr(self, model_class.__name__.lower(), model_class)
            
            # 4. 更加安全的字段检查逻辑 (替代 regex)
            # 获取数据库中该表实际存在的列名
            columns = [c.name for c in self.connect.get_columns(model_class._meta.table_name)]
            
            # 遍历模型定义的所有字段
            for field_name, field_obj in model_class._meta.fields.items():
                if field_name not in columns:
                    print(f"检测到缺失字段，正在自动添加: {model_class.__name__}.{field_name}")
                    try:
                        migrate(
                            migrator.add_column(model_class._meta.table_name, field_name, field_obj)
                        )
                    except OperationalError as e:
                        # 忽略 "duplicate column name" 错误，防止并发下的竞争条件
                        if 'duplicate column name' not in str(e).lower():
                            raise e

    def __del__(self):
        if not self.connect.is_closed():
            self.connect.close()

# 实例化
db = _Db()