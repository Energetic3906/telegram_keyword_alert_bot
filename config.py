#coding=utf-8
import sys
import yaml
from pathlib import Path

__all__ = [
  'config',
  '_current_path'
]

# 1. 使用 pathlib 获取当前路径 (更稳健，跨平台)
# resolve() 会解析符号链接并获取绝对路径
_base_path = Path(__file__).resolve().parent

# 为了保持对旧代码的兼容性 (如果有代码依赖它是字符串)，将其转为 str
_current_path = str(_base_path)

config_file = _base_path / 'config.yml'
default_config_file = _base_path / 'config.yml.default'

# 2. 检查配置文件是否存在
if not config_file.exists():
    print(f"\n❌ Critical Error: Config file not found!")
    print(f"   Path searched: {config_file}")
    print(f"💡 Solution: Please copy the default config file and configure it.")
    
    if default_config_file.exists():
        print(f"   Command example: cp config.yml.default config.yml\n")
    else:
        print(f"   (Note: 'config.yml.default' was not found either)\n")
        
    sys.exit(1)

# 3. 安全读取配置文件
try:
    # 强制指定 encoding='utf-8'，防止 Windows 下因编码问题(GBK)导致读取中文或 Emoji 报错
    with open(config_file, 'r', encoding='utf-8') as _f:
        # yaml.safe_load 是 load(..., Loader=yaml.SafeLoader) 的官方推荐简写
        config = yaml.safe_load(_f)

    # 防止配置文件为空导致后续代码报错
    if config is None:
        print(f"⚠️ Warning: '{config_file.name}' exists but is empty.")
        config = {}

except yaml.YAMLError as e:
    print(f"\n❌ Error parsing config file '{config_file.name}':")
    if hasattr(e, 'problem_mark'):
        mark = e.problem_mark
        print(f"   Line {mark.line + 1}, Column {mark.column + 1}: {e.problem}")
    else:
        print(f"   {e}")
    sys.exit(1)

except Exception as e:
    print(f"\n❌ Unexpected error loading config: {e}")
    sys.exit(1)