import asyncio
import os
import random
import re
import traceback

import aiofiles
import yt_dlp
from colorama import Fore, init
from vk_api.exceptions import ApiError

from core.logger import log
from core.vkapi import VKAPI

init(autoreset=True)
t = 0


class VKDownloader(VKAPI):
    async def download_video(self, video_url, save_dir, cache_file):
        video_id = re.search(r'id=(\d+)', video_url).group(1)
        output_file = os.path.join(save_dir, f'{video_id}.mp4')

        # if await self.check_cache(cache_file, video_id):
        #     print(Fore.GREEN + f'Клип уже скачан: {output_file}')
        #     return output_file

        ydl_opts = {
            'quiet': True,
            'outtmpl': output_file,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
            'proxy': random.choice(self.proxies) if self.proxies else None,
        }

        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                self._download,
                video_url,
                ydl_opts,
                output_file,
                save_dir,
                cache_file,
            )
            print(Fore.CYAN + f'Клип успешно скачан: {output_file}')
            return output_file
        except Exception:
            log.error(
                Fore.RED + f'Ошибка скачивания:\n{traceback.format_exc()}'
            )
            return output_file

    def _download(
        self, video_url, ydl_opts, output_file, save_dir, cache_file
    ):
        video_id = re.search(r'id=(\d+)', video_url).group(1)
        output_file = os.path.join(save_dir, f'{video_id}.mp4')

        if self.check_cache(cache_file, video_id):
            print(Fore.GREEN + f'Клип уже скачан: {output_file}')
            return output_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

    async def fetch_video_urls(self, count=200):
        videos, offset = [], 0
        while True:
            print(
                Fore.YELLOW
                + f'Формирую список ссылок всех клипов группы: {self.group_title}: {len(videos)}'
            )
            try:
                response = self.vk_session.video.get(
                    owner_id=self.group_id,
                    album_id=-6,
                    offset=offset,
                    count=count,
                )
                items = response.get('items', [])
                if not items:
                    break

                videos.extend(
                    video['player']
                    for video in items
                    if video.get('player') not in videos
                )
                offset += count
            except ApiError:
                log.error(
                    Fore.RED + f'Ошибка API VK: {traceback.format_exc()}'
                )
                break
        return videos

    async def download_videos_from_group(self, group_link):
        if not self.vk_session:
            await self.get_vk_api()

        await self.get_group_id_and_name(group_link)
        save_dir = os.path.join('clips', f'Группа_{self.group_title}')
        cache_file = os.path.join('cache', f'{self.group_title}.txt')
        os.makedirs(save_dir, exist_ok=True)

        video_urls = await self.fetch_video_urls()
        await asyncio.gather(
            *[
                self.download_video(url, save_dir, cache_file)
                for url in video_urls
            ]
        )
