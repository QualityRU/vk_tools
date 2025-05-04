import logging

import requests
from colorlog import ColoredFormatter

from core.utils import MethodDict, read_config


def config():
    return MethodDict(read_config('config.json'))


LOG_LEVEL = logging.DEBUG
LOGFORMAT = '%(log_color)s[VK Tools Bot]%(reset)s[%(log_color)s%(levelname)s%(reset)s] %(asctime)s %(log_color)s%(message)s%(reset)s'


class TelegramHandler(logging.Handler):
    def emit(self, record):
        cfg = config()
        try:
            message = f'[{record.levelname}] {record.getMessage()}'
            if record.levelno >= logging.ERROR:
                requests.post(
                    f'https://api.telegram.org/bot{cfg.telegram.TELEGRAM_TOKEN}/sendMessage',
                    data={
                        'chat_id': cfg.telegram.TELEGRAM_CHAT_ID,
                        'text': message,
                        'parse_mode': 'HTML',
                    },
                )
        except Exception as e:
            print('Failed to send log to Telegram:', e)


formatter = ColoredFormatter(LOGFORMAT, '%Y-%m-%d %H:%M:%S')
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)

telegram_handler = TelegramHandler()
telegram_handler.setLevel(logging.ERROR)
telegram_handler.setFormatter(
    logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s')
)

log = logging.getLogger('pythonConfig')
log.setLevel(LOG_LEVEL)
log.addHandler(stream)
log.addHandler(telegram_handler)
