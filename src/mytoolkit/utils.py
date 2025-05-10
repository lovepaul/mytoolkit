# src/mytoolkit/utils.py

import os
import logging
from datetime import datetime
from colorama import init as _colorama_init, Fore, Style

# 初始化 colorama，跨平台支持
_colorama_init(autoreset=True)

# 日志根目录
LOG_ROOT = os.path.join(os.getcwd(), "logs")


def get_logger(cmd_name: str) -> logging.Logger:
    """
    创建并返回一个 Logger：
      - 只写文件（logs/<cmd_name>/<timestamp>.log）
      - 不向控制台打印（交给 typer.echo 输出）
    """
    os.makedirs(LOG_ROOT, exist_ok=True)
    cmd_dir = os.path.join(LOG_ROOT, cmd_name)
    os.makedirs(cmd_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(cmd_dir, f"{timestamp}.log")

    logger = logging.getLogger(cmd_name)
    logger.setLevel(logging.INFO)
    # 如果已经有 FileHandler，就直接返回
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return logger

    # 只添加文件 Handler
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    return logger


def echo_info(msg: str):
    """绿色输出到终端"""
    print(Fore.GREEN + msg + Style.RESET_ALL)


def echo_error(msg: str):
    """红色输出到终端"""
    print(Fore.RED + msg + Style.RESET_ALL)
