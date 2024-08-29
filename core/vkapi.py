import os
import random
import traceback

import aiofiles
import vk_api
from colorama import Fore


class VKAPI:
    def __init__(self, login=None, password=None, tokens=None, proxies=None):
        self.tokens = tokens
        self.login = login
        self.password = password
        self.proxies = proxies
        self.vk_session = None
        self.group_id = None
        self.group_title = None

    async def get_vk_api(self):
        if self.vk_session:
            return self.vk_session

        try:
            if self.login and self.password:
                vk = vk_api.VkApi(login=self.login, password=self.password)
                vk.auth()
            else:
                token = random.choice(self.tokens)
                vk = vk_api.VkApi(token=token)

            self.vk_session = vk.get_api()
            return self.vk_session
        except vk_api.exceptions.ApiError:
            print(Fore.RED + 'Ошибка авторизации')
            raise ValueError('Ошибка авторизации')
        except Exception as e:
            print(Fore.RED + f'Ошибка при авторизации: {e}')
            raise

    async def get_group_id_and_name(self, group_link):
        if not self.vk_session:
            await self.get_vk_api()

        try:
            group_name = group_link.strip('/').split('/')[-1]
            group_info = self.vk_session.groups.getById(
                group_id=group_name, fields='id'
            )[0]
            self.group_id = -group_info['id']
            self.group_title = group_info['name']
            return self.group_id
        except Exception as e:
            print(
                Fore.RED
                + f'Ошибка при получении ID и названия группы: {group_link}. Ошибка: {traceback.format_exc()}'
            )
            raise ValueError(
                f'Ошибка при получении ID и названия группы: {group_link}. Ошибка: {traceback.format_exc()}'
            )

    def check_cache(self, cache_file, video_id):
        if not os.path.exists(cache_file):
            open(cache_file, 'w').close()
        with open(cache_file, mode='r') as cache:
            downloaded_ids = cache.read().splitlines()
        if video_id in downloaded_ids:
            return True
        with open(cache_file, mode='a') as cache:
            cache.write(video_id + '\n')
            return False
