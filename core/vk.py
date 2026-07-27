import asyncio
import json
import os
import random
import re
from os.path import getsize
from traceback import format_exc
from urllib.parse import parse_qs, urlparse

import aiohttp
import vk_api
import yt_dlp
from colorama import Fore

from core.logger import log


class VKAPI:
    def __init__(self, token=None, login=None, password=None):
        self.token = token
        self.login = login
        self.password = password
        self.vk_session = None

    async def get_vk_api(self):
        if self.vk_session:
            return self.vk_session

        try:
            def create_api():
                vk = (
                    vk_api.VkApi(token=self.token, api_version='5.282')
                    if self.token
                    else vk_api.VkApi(
                        login=self.login,
                        password=self.password,
                        api_version='5.282',
                    )
                )
                if self.login and self.password:
                    vk.auth()
                return vk.get_api()

            self.vk_session = await asyncio.to_thread(create_api)
            return self.vk_session
        except Exception:
            log.error(f'Ошибка при авторизации: {format_exc()}')
            raise

    async def get_group_id_and_name(self, group_link):
        if not self.vk_session:
            await self.get_vk_api()

        try:
            group_name = group_link.strip('/').split('/')[-1]
            group_info = await asyncio.to_thread(
                self.vk_session.groups.getById,
                group_ids=group_name,
                fields='id',
            )
            group_id = -group_info['groups'][0]['id']
            group_title = group_info['groups'][0]['name']
            return group_id, group_title
        except Exception:
            log.error(
                f'Ошибка при получении данных группы:\n{format_exc()}\n{group_link}'
            )
            return None


class VKDownloader(VKAPI):
    async def fetch_video_urls(self, group_links, cache_name, video_limit):
        video_urls = []
        all_video_urls = await self.collect_all_video_urls(
            group_links, cache_name
        )
        random.shuffle(all_video_urls)

        for video_url, cache_key in all_video_urls:
            if len(video_urls) >= video_limit:
                break
            if not self.check_cache(cache_key, cache_name):
                video_urls.append((video_url, cache_key))

        return video_urls[:video_limit]

    async def collect_all_video_urls(self, group_links, cache_name):
        all_video_urls = []
        random.shuffle(group_links)

        for group_link in group_links:
            try:
                group = await self.get_group_id_and_name(group_link)
            except Exception:
                log.error(
                    f'Ошибка при получении данных группы:\n{format_exc()}\n{group_link}'
                )
                continue
            if group is None:
                continue

            group_id, _ = group
            if group_id >= 0:
                log.error(
                    f'Некорректный group_id: {group_id} для группы {group_link}'
                )
                continue

            count_video = await self.get_video_count(group_id, group_link)

            if count_video == 0:
                continue

            attempts = min(10, max(1, (count_video + 99) // 100))
            for _ in range(attempts):
                video_urls_from_group = await self.get_random_videos(
                    group_id, group_link, cache_name, count_video
                )
                log.info(
                    str(group_link) + ' ссылок ' + str(len(all_video_urls))
                )
                if video_urls_from_group:
                    all_video_urls.extend(video_urls_from_group)
                    break
            else:
                log.info(f'Нет новых роликов в группе {group_link}.')

        return all_video_urls

    async def get_video_count(self, group_id, group_link):
        try:
            response = await asyncio.to_thread(
                self.vk_session.shortVideo.getOwnerVideos,
                owner_id=group_id,
                track_code='',
                count=1,
            )
            return response.get('count', 0)
        except Exception:
            log.error(
                f'Ошибка при получении количества видео из {group_link}:\n{format_exc()}'
            )
            return 0

    async def get_random_videos(
        self, group_id, group_link, cache_name, count_video
    ):
        try:
            offset = random.randint(0, max(0, count_video - 100))
            response = await asyncio.to_thread(
                self.vk_session.shortVideo.getOwnerVideos,
                owner_id=group_id,
                track_code='',
                offset=offset,
                count=100,
            )
            items = response.get('items', [])
            return [
                (
                    video['player'],
                    f"{video.get('owner_id', group_id)}_{video['id']}",
                )
                for video in items
                if not self.check_cache(
                    f"{video.get('owner_id', group_id)}_{video['id']}", cache_name
                )
            ]
        except Exception:
            log.error(
                f'Ошибка при получении видео из группы {group_link}: {group_id}:\n{format_exc()}'
            )
            return []

    def check_cache(self, video_id, cache_name):
        cache_file = os.path.join('cache', f'{cache_name}.txt')
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)

        if not os.path.exists(cache_file):
            open(cache_file, 'w').close()

        with open(cache_file, 'r') as file:
            cached_ids = set(file.read().splitlines())
        legacy_id = video_id.rsplit('_', 1)[-1]
        return video_id in cached_ids or legacy_id in cached_ids

    def update_cache(self, video_id, cache_name):
        cache_file = os.path.join('cache', f'{cache_name}.txt')
        with open(cache_file, 'a') as file:
            file.write(f'{video_id}\n')

    @staticmethod
    def video_identifiers(video_url):
        query = parse_qs(urlparse(video_url).query)
        owner_id = query.get('oid', [None])[0]
        video_id = query.get('id', [None])[0]
        if owner_id and video_id:
            return owner_id, video_id

        match = re.search(r'video(-?\d+)_(\d+)', video_url)
        if match:
            return match.groups()
        raise ValueError(f'Не удалось извлечь идентификаторы видео из {video_url}')

    async def download_video(self, video_url, cache_name, cache_key=None):
        owner_id, video_id = self.video_identifiers(video_url)
        save_dir = os.path.join('clips')
        os.makedirs(save_dir, exist_ok=True)
        output_file = os.path.join(save_dir, f'{cache_name}_{owner_id}_{video_id}.mp4')

        ydl_opts = {
            'outtmpl': output_file,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'quiet': True,
        }
        canonical_url = f'https://vk.ru/video{owner_id}_{video_id}'

        try:
            log.info(canonical_url)

            def run_download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([canonical_url])

            await asyncio.to_thread(run_download)
            log.info(Fore.CYAN + f'Клип успешно скачан: {output_file}')
            self.update_cache(cache_key or f'{owner_id}_{video_id}', cache_name)
            return output_file
        except yt_dlp.DownloadError as e:
            log.error(f'Ошибка скачивания: {e}\n{canonical_url}')
        except Exception:
            log.error(f'Ошибка скачивания:\n{format_exc()}\n{canonical_url}')
        return None


class VKUploader(VKAPI):
    async def upload_videos(
        self,
        clips_path,
        group_to_upload,
        cache_name,
        description='',
        wallpost=1,
    ):
        group = await self.get_group_id_and_name(group_to_upload)
        if group is None:
            return
        group_upload_id, _ = group
        for root, _, files in os.walk(clips_path):
            for file in files:
                if file.startswith(cache_name) and file.endswith('.mp4'):
                    video_path = os.path.join(root, file)
                    success = await self.upload_clip(
                        abs(group_upload_id), video_path, description, wallpost
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

    async def upload_video_path(self, group_to_upload, video_path, description='', wallpost=1):
        group = await self.get_group_id_and_name(group_to_upload)
        if group is None:
            return False
        return await self.upload_clip(abs(group[0]), video_path, description, wallpost)

    async def upload_clip(
        self, group_upload_id, video_path, description='', wallpost=1
    ):
        try:
            a = await asyncio.to_thread(
                self.vk_session.shortVideo.create,
                group_id=group_upload_id,
                v=5.282,
                file_size=getsize(video_path),
                wallpost=wallpost,
                description=description,
            )
            upload_url = a['upload_url']
            with open(video_path, 'rb') as file:
                data = {'file': file}
                async with aiohttp.ClientSession() as session:
                    async with session.post(upload_url, data=data) as res:
                        res_text = await res.text()

            if not self.contains_json(res_text):
                return self.upload_old(res_text, video_path)
            return await self.upload(res_text, video_path, description, wallpost)
        except Exception:
            log.error(f'Ошибка загрузки:\n{format_exc()}')
            return False

    async def upload(self, res, video_path, description, wallpost):
        try:
            response_json = json.loads(res)

            await asyncio.sleep(120)

            await asyncio.to_thread(
                self.vk_session.shortVideo.edit,
                video_id=response_json['video_id'],
                owner_id=response_json['owner_id'],
                description=description,
                privacy_view='all',
                can_make_duet=1,
            )

            publish_result = await asyncio.to_thread(
                self.vk_session.shortVideo.publish,
                video_id=response_json['video_id'],
                owner_id=response_json['owner_id'],
                license_agree=1,
                publish_date=0,
                wallpost=wallpost,
            )
            if 'video' in publish_result:
                log.info(Fore.CYAN + f'Клип {video_path} успешно залит!')
                return True
            else:
                log.error(Fore.RED + f'Клип {video_path} не залит!')
        except vk_api.ApiError as e:
            if e.code == 100:
                log.error('Ошибка VK API: Видео еще не обработано.')
                return False
            elif e.code == 9:
                log.error('Ошибка VK API 9: Flood control...')
                return False
            elif e.code == 3:
                log.error('Ошибка VK API: неизвестный метод')
                return False
            else:
                log.error(format_exc())
                return False
        except Exception:
            log.error(f'Ошибка загрузки:\n{format_exc()}')
            return False

    def upload_old(self, res, video_path):
        if res == '<retval>1</retval>':
            log.info(Fore.CYAN + f'Клип {video_path} успешно залит!')
            return True
        elif 'Flood control' in res:
            log.error('Превышен лимит запросов. Повторная попытка через час.')
            return False
        else:
            log.error(f'Клип {video_path} не залит! Ответ: {res}')
            return False

    def contains_json(self, str):
        try:
            json.loads(str)
        except (json.JSONDecodeError, TypeError):
            return False
        return True
