import asyncio
import json
import re

import aiofiles
import vk_api
from colorama import Fore, init
from vk_api.exceptions import ApiError

from core.logger import log

init(autoreset=True)


class MethodDict:
    def __init__(self, data=None):
        self._dict = self._convert_dict(data if data is not None else {})

    def _convert_dict(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = MethodDict(value)
        return data

    def __getattr__(self, name):
        if name in self._dict:
            return self._dict[name]
        raise AttributeError(f"'MethodDict' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._dict[name] = self._convert_dict({name: value})[name]

    def __delattr__(self, name):
        if name in self._dict:
            del self._dict[name]
        else:
            raise AttributeError(
                f"'MethodDict' object has no attribute '{name}'"
            )

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()


async def read_config(file_path):
    async with aiofiles.open(file_path, mode='r') as file:
        content = await file.read()
        config = json.loads(content)
    return config


async def read_lines(file_path):
    async with aiofiles.open(file_path, mode='r') as file:
        return [line.strip() async for line in file]


async def read_proxies(file_path):
    proxies = []
    async with aiofiles.open(file_path, mode='r') as file:
        async for line in file:
            proxy = line.strip()
            if re.match(r'^\d+\.\d+\.\d+\.\d+:\d+:\w+:\w+$', proxy):
                ip, port, username, password = proxy.split(':')
                proxies.append(f'http://{username}:{password}@{ip}:{port}')
            else:
                log.error(f'Неверный формат прокси: {proxy}')
    return proxies


async def validate_token(token):
    try:
        vk_session = vk_api.VkApi(token=token)
        vk = vk_session.get_api()
        vk.account.getInfo()
        return token
    except (ApiError, Exception) as e:
        log.error(f'Ошибка при проверке токена {token}: {e}')
        return None


async def get_valid_tokens(tokens):
    return [
        token
        for token in await asyncio.gather(
            *(validate_token(token) for token in tokens)
        )
        if token
    ]
