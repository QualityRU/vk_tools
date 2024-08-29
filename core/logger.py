import asyncio
import logging

import aiohttp
from colorlog import ColoredFormatter

from core.config import telegramBotLogging


class TelegramLogger:
    def __init__(self, telegram_chat_id, account_name):
        self.telegram_chat_id = telegram_chat_id
        self.account_name = account_name

    async def send_telegram_log(self, message, level='error'):
        if (
            not telegramBotLogging['is_active']
            or not self.telegram_chat_id
            or not telegramBotLogging['bot_token']
        ):
            logging.warning(
                'Бот Telegram не активен или отсутствуют учетные данные'
            )
            return

        if not telegramBotLogging['messages'].get(level, False):
            logging.warning(f'Сообщения для уровня "{level}" не включены')
            return

        message = f'{level.upper()}:\n{message}'

        url = f"https://api.telegram.org/bot{telegramBotLogging['bot_token']}/sendMessage"
        params = {'chat_id': self.telegram_chat_id, 'text': message}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        logging.error(
                            f'Не удалось отправить сообщение в Telegram: {response.status} - {response_text}'
                        )
        except asyncio.CancelledError:
            logging.error(f'[{self.account_name}] Задача была отменена')
        except Exception as e:
            logging.error(f'[{self.account_name}] Ошибка TelegramLog: {e}')


class TelegramLogHandler(logging.Handler):
    def __init__(self, telegram_logger, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telegram_logger = telegram_logger
        self.loop = asyncio.get_event_loop()

    def emit(self, record):
        log_entry = self.format(record)
        level = record.levelname.lower()
        # Schedule the asynchronous task
        self.loop.create_task(
            self.telegram_logger.send_telegram_log(log_entry, level=level)
        )


LOG_LEVEL = logging.DEBUG
LOGFORMAT = '%(log_color)s[VK Tools Bot]%(reset)s[%(log_color)s%(levelname)s%(reset)s] %(asctime)s %(log_color)s%(message)s%(reset)s'
formatter = ColoredFormatter(LOGFORMAT, '%Y-%m-%d %H:%M:%S')
stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)
log = logging.getLogger('pythonConfig')
log.setLevel(LOG_LEVEL)
log.addHandler(stream)

telegram_logger = TelegramLogger(
    telegram_chat_id=telegramBotLogging['telegram_chat_id'],
    account_name='test',
)

telegram_handler = TelegramLogHandler(telegram_logger)
telegram_handler.setLevel(logging.DEBUG)
log.addHandler(telegram_handler)
