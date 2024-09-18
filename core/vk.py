import asyncio
import os
import random
import re
import traceback
from os.path import getsize

import aiohttp
import vk_api
import yt_dlp
from colorama import Fore

from core.logger import log


class VKAPI:
    def __init__(self, tokens=None, login=None, password=None):
        self.tokens = tokens
        self.login = login
        self.password = password
        self.vk_session = None

    async def get_vk_api(self):
        if self.vk_session:
            return self.vk_session

        try:
            vk = (
                vk_api.VkApi(token=random.choice(self.tokens))
                if self.tokens
                else vk_api.VkApi(login=self.login, password=self.password)
            )
            vk.auth() if self.login and self.password else None
            self.vk_session = vk.get_api()
            return self.vk_session
        except vk_api.exceptions.ApiError:
            log.error('Ошибка авторизации')
            raise ValueError('Ошибка авторизации')
        except Exception as e:
            log.error(f'Ошибка при авторизации: {e}')
            raise

    async def get_group_id_and_name(self, group_link):
        if not self.vk_session:
            await self.get_vk_api()

        try:
            group_name = group_link.strip('/').split('/')[-1]
            group_info = self.vk_session.groups.getById(
                group_id=group_name, fields='id'
            )[0]
            group_id = -group_info['id']
            group_title = group_info['name']
            return group_id, group_title
        except Exception:
            log.error(
                f'Ошибка при получении данных группы: {traceback.format_exc()}'
            )
            raise ValueError(
                f'Ошибка при получении данных группы: {traceback.format_exc()}'
            )


class VKDownloader(VKAPI):
    async def fetch_video_urls(self, group_links, cache_name, video_limit):
        video_urls = []
        all_video_urls = await self.collect_all_video_urls(
            group_links, cache_name
        )
        random.shuffle(all_video_urls)

        for video_url, video_id in all_video_urls:
            if len(video_urls) >= video_limit:
                break
            if not self.check_cache(video_id, cache_name):
                video_urls.append(video_url)

        return video_urls[:video_limit]

    async def collect_all_video_urls(self, group_links, cache_name):
        all_video_urls = []
        random.shuffle(group_links)

        for group_link in group_links:
            group_id, group_title = await self.get_group_id_and_name(
                group_link
            )

            if abs(group_id) <= 0:  # Проверка на корректность group_id
                log.error(
                    f'Некорректный group_id: {group_id} для группы {group_link}'
                )
                continue

            count_video = await self.get_video_count(group_id, group_link)

            if count_video == 0:
                continue

            while True:
                video_urls_from_group = await self.get_random_videos(
                    group_id, group_link, cache_name, count_video
                )
                if video_urls_from_group:
                    all_video_urls.extend(video_urls_from_group)
                    break

        return all_video_urls

    async def get_video_count(self, group_id, group_link):
        try:
            response = self.vk_session.video.get(
                owner_id=group_id, album_id=-6, offset=0, count=1
            )
            return response.get('count', 0)
        except Exception as e:
            log.error(
                f'Ошибка при получении количества видео из группы {group_link}: {e}'
            )
            return 0

    async def get_random_videos(
        self, group_id, group_link, cache_name, count_video
    ):
        try:
            offset = random.randint(0, max(0, count_video - 1))
            response = self.vk_session.video.get(
                owner_id=group_id, album_id=-6, offset=offset, count=200
            )

            items = response.get('items', [])
            return [
                (video['player'], video['id'])
                for video in items
                if not self.check_cache(video['id'], cache_name)
            ]
        except Exception as e:
            log.error(
                f'Ошибка при получении видео из группы {group_link}: {group_id}: {e}'
            )
            return []

    def check_cache(self, video_id, cache_name):
        cache_file = os.path.join('cache', f'{cache_name}.txt')
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        if not os.path.exists(cache_file):
            open(cache_file, 'w').close()

        with open(cache_file, 'r') as file:
            return video_id in file.read().splitlines()

    def update_cache(self, video_id, cache_name):
        cache_file = os.path.join('cache', f'{cache_name}.txt')
        with open(cache_file, 'a') as file:
            file.write(f'{video_id}\n')

    async def download_video(self, video_url, cache_name):
        video_id = re.search(r'id=(\d+)', video_url).group(1)
        save_dir = os.path.join('clips')
        os.makedirs(save_dir, exist_ok=True)
        output_file = os.path.join(save_dir, f'{cache_name}_{video_id}.mp4')

        ydl_opts = {
            'outtmpl': output_file,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'quiet': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            log.info(Fore.CYAN + f'Клип успешно скачан: {output_file}')
            self.update_cache(video_id, cache_name)
        except Exception:
            log.error(f'Ошибка скачивания: {traceback.format_exc()}')


class VKUploader(VKAPI):
    async def upload_videos(
        self,
        clips_path,
        group_to_upload,
        cache_name,
        description='',
        wallpost=0,
    ):
        group_upload_id, _ = await self.get_group_id_and_name(group_to_upload)
        for root, _, files in os.walk(clips_path):
            for file in files:
                if file.startswith(cache_name) and file.endswith('.mp4'):
                    video_path = os.path.join(root, file)
                    success = await self.upload_clip(
                        abs(group_upload_id), video_path, description
                    )
                    if success:
                        os.remove(video_path)
                    else:
                        log.info(
                            Fore.YELLOW
                            + 'Ожидание перед повторной попыткой...'
                        )
                        await asyncio.sleep(900)
                    await asyncio.sleep(5)

    async def upload_clip(
        self, group_upload_id, video_path, description='', wallpost=0
    ):
        try:
            a = self.vk_session.shortVideo.create(
                group_id=group_upload_id,
                v=5.241,
                wallpost=wallpost,
                description=description,
                file_size=getsize(video_path),
            )
            upload_url = a['upload_url']
            data = {'file': open(video_path, 'rb')}

            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=data) as res:
                    response_text = await res.text()
                    if (
                        res.status == 200
                        and response_text == '<retval>1</retval>'
                    ):
                        log.info(
                            Fore.CYAN + f'Клип {video_path} успешно залит!'
                        )
                    elif (
                        res.status == 200 and 'Flood control' in response_text
                    ):
                        log.error(
                            'Превышен лимит запросов. Повторная попытка через час.'
                        )
                        return False
                    else:
                        log.error(
                            f'Клип {video_path} не залит! Ответ: {response_text}'
                        )
                        return False

        except Exception as e:
            log.error(f'Ошибка загрузки: {e}')
            return False

        return True
