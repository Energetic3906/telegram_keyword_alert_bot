#coding=utf-8
from config import config
from colorama import Fore, Style, init
from text_box_wrapper import wrap
from logger import logger

# 适配新的数据库模块导入
from db.utils import User, User_block_list, db

# 尝试导入版本号，如果不存在则使用默认值
try:
    from .__version__ import __version__
except ImportError:
    __version__ = "2024.02.01"

def is_allow_access(chat_id) -> bool:
    '''
    检查当前chat_id有权限使用bot
    Args:
        chat_id (_type_): Telegram chat id
    Returns:
        bool: 是否允许使用
    '''
    # 非公共服务
    if 'private_service' in config and config['private_service']:
        if 'authorized_users' in config:
            # 只服务指定的用户
            # 确保配置中的ID和传入的ID类型一致（通常配置里是int）
            if chat_id in config['authorized_users']:
                return True
            return False
    return True

def read_tag_from_file(filename="version.txt"):
    '''
    获取tag信息
    '''
    return __version__

@wrap(border_string='##', min_padding=2)
def banner():
    init()  # 初始化colorama
    green_circle = f"{Fore.GREEN}● success{Style.RESET_ALL}\n"
    tag = read_tag_from_file()
    message = f"{green_circle} 🤖️Telegram keyword alert bot (Version: {tag})"
    return message

def is_msg_block(receiver, msg, channel_name, channel_id):
    """
    消息黑名单检查
    Args:
        receiver : 消息接收用户 chat id
        msg : 消息内容
        channel_name : 消息发送的频道名称
        channel_id : 消息发送的频道id

    Returns:
        Bool: True 命中黑名单 不发送消息，False 无命中 发送消息
    """
    # 1. 获取用户
    user = User.get_or_none(chat_id=receiver)
    
    # [修复] 如果用户不存在，直接返回 False (不拦截)，防止 user.id 报错
    if not user:
        return False

    # 2. 检查长度限制 (Length Limit)
    # 使用 ORM 查询替代原生 SQL，更安全且利用了新版 db/utils.py 的模型
    blacklist_type = 'length_limit'
    
    block_rule = User_block_list.get_or_none(
        user_id=user.id, 
        blacklist_type=blacklist_type
    )

    if block_rule:
        try:
            limit = int(block_rule.blacklist_value)
            msg_len = len(msg)
            
            if limit > 0 and msg_len > limit:
                logger.info(f'block_list_check refuse send. receiver:{receiver}, limit:{limit}, msg_len:{msg_len}')
                return True
        except ValueError:
            logger.error(f"Invalid blacklist value for user {user.id}: {block_rule.blacklist_value}")
            
    return False

def get_event_chat_username(event_chat):
    '''
    获取群组/频道的单个用户名
    '''
    if hasattr(event_chat, 'username') and event_chat.username:
        return event_chat.username
    
    if hasattr(event_chat, 'usernames') and event_chat.usernames:
        standby_username = '' # 备选用户名
        for i in event_chat.usernames:
            if i.active and not i.editable and i.username: # 激活的用户名且不可编辑.优先读取
                return i.username
            if i.active and i.username: # 激活的用户名.备选读取
                standby_username = i.username
        
        if standby_username:
            return standby_username
    
    return None

def get_event_chat_username_list(event_chat):
    '''
    获取群组/频道的所有用户名列表
    '''
    result = []
    if hasattr(event_chat, 'username') and event_chat.username:
        result.append(event_chat.username)
    
    if hasattr(event_chat, 'usernames') and event_chat.usernames:
        for i in event_chat.usernames:
            if i.active and i.username: # 激活的用户名
                result.append(i.username)
    
    return list(set(result))