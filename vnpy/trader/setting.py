"""
Global setting of VN Trader.
"""

from logging import CRITICAL,INFO

from .utility import load_json, get_reg

SETTINGS = {
    "tradeagent.trading_boards": 4,
    "font.family": "Arial",
    "font.size": 12,

    "log.active": True,
    "log.level": INFO,#CRITICAL,
    "log.console": True,
    "log.file": True,
}
SETTINGS_CN = {
    "tradeagent.trading_boards": "交易窗口数量",
    "font.family": "字体",
    "font.size": "字体大小",

    "log.active": "日志开关",
    "log.level": "日志级别",
    "log.console": "日志后台开关",
    "log.file": "日志文件",
}

# Load global setting from json file.
SETTING_FILENAME = "vt_setting.json"
SETTINGS.update(get_reg(SETTING_FILENAME))


def get_settings(prefix: str = ""):
    prefix_length = len(prefix)
    return {k[prefix_length:]: v for k, v in SETTINGS.items() if k.startswith(prefix)}
