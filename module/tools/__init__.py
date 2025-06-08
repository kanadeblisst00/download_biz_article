import os
import sys
from loguru import logger
import configparser
from ..settings import ROOT_DIR

def read_ini_file():
    config_path = os.path.join(ROOT_DIR, "config.ini")
    if not os.path.exists(config_path):
        return {}
    config = configparser.ConfigParser()
    config.read(config_path)
    config_dict = {}
    for section in config.sections():
        config_dict[section] = dict(config.items(section))
    logger.info(f"读取配置文件: {config_path}, 配置内容: {config_dict}")
    return config_dict