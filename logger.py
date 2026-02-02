#coding=utf-8
import logging, os, sys
from logging.handlers import RotatingFileHandler
from config import _current_path, config

__all__ = [
    'logger'
]

# --- 1. 配置日志路径 ---
__LOG_DIR = f'{_current_path}/logs/'
__LOG_NAME = 'keyword_alert.log'

# 从配置中读取路径，如果存在则覆盖默认值
if config.get('logger', {}).get('path'):
    __LOG_DIR = config['logger']['path'].rstrip('/')

# 自动创建日志目录
if not os.path.exists(__LOG_DIR):
    os.makedirs(__LOG_DIR)

__LOG_FILE = f"{__LOG_DIR}/{__LOG_NAME}"

# --- 2. 配置日志级别 ---
# 获取配置中的 level，默认为 INFO
config_level = config.get('logger', {}).get('level', 'INFO')
# 安全获取 logging 模块中的级别常量 (如 logging.INFO, logging.ERROR)
__level = getattr(logging, config_level) if hasattr(logging, config_level) else logging.INFO

# --- 3. 定义通用的日志格式 ---
# 格式：[级别][记录器名称][时间]-->消息
formatter = logging.Formatter(
    fmt='[%(levelname)s][%(name)s][%(asctime)s] --> %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S%Z'
)

# --- 4. 初始化 Handler ---

# Handler A: 文件输出 (RotatingFileHandler)
# maxBytes=5MB, backupCount=10 (保留最近10个文件)
file_handler = RotatingFileHandler(__LOG_FILE, maxBytes=5*1024*1024, backupCount=10)
file_handler.setFormatter(formatter)
file_handler.setLevel(__level)

# Handler B: 控制台/Docker输出 (StreamHandler)
# 输出到标准输出 stdout，这样 'docker logs' 命令就能看到了
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(__level)

# --- 5. 初始化 Logger ---
logger = logging.getLogger('keyword_alert.root')
logger.setLevel(__level)

# 添加 Handler
logger.addHandler(file_handler)
logger.addHandler(console_handler)