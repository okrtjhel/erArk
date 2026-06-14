import sys

# 强制标准输出/错误流使用UTF-8编码，避免在简体中文以外的Windows控制台（如cp950）下打印中文时崩溃
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from Script.Core import game_type, cache_control
from Script.Config import normal_config

cache_control.cache = game_type.Cache()
normal_config.init_normal_config()


from Script.Config import game_config, name_config

game_config.init()
# name_config.init_name_data()


from Script.Config import map_config


map_config.init_map_data()


print("Cache Building End")
