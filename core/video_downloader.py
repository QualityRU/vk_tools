import asyncio
import os
import random

from aiohttp import ClientSession

# from instagrapi import AsyncClient as InstaClient
from vk_api import VkApi
from vk_api.exceptions import VkApiError
from vk_api.upload import VkUpload
from yt_dlp import YoutubeDL


class VideoDownloaderAsync:
    def __init__(self):
        self.videos = []

    async def download_from_vkontakte(self, vk_login, vk_password):
        vk_session = VkApi(login=vk_login, password=vk_password)
        vk_session.auth()
        vk = vk_session.get_api()

        # Получаем список последних видео из группы
        videos = vk.video.get(count=10)['items']
        video_links = [
            f"https://vk.com/video{video['owner_id']}_{video['id']}"
            for video in videos[:5]
        ]
        await self._download_videos(video_links, 'VK')

    async def download_from_youtube(self, playlist_url):
        ydl_opts = {'quiet': True, 'noplaylist': True, 'extract_flat': True}
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'videos/%(title)s.%(ext)s',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            },
        }
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(playlist_url, download=False)
            print(info_dict)
            video_links = [
                f"https://www.youtube.com/watch?v={entry['id']}"
                for entry in info_dict['entries'][:5]
            ]
        await self._download_videos(video_links, 'YouTube Shorts')

    async def download_from_instagram(self, insta_username, insta_password):
        client = InstaClient()
        await client.login(insta_username, insta_password)
        reels = await client.clips_user_feed(insta_username, amount=5)
        video_links = [reel.video_url for reel in reels]
        await self._download_videos(video_links, 'Instagram')

    async def download_from_tiktok(self):
        ydl_opts = {'quiet': True}
        tiktok_url = 'https://www.tiktok.com/tag/foryou'
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=False)
            print(info_dict)
            video_links = [
                f"https://www.tiktok.com/@{entry['author']}/video/{entry['id']}"
                for entry in info_dict['entries'][:5]
            ]
        await self._download_videos(video_links, 'TikTok')

    async def _download_videos(self, urls, platform):
        ydl_opts = {
            'format': 'best',
            'outtmpl': f'videos/{platform}/%(title)s.%(ext)s',
        }
        with YoutubeDL(ydl_opts) as ydl:
            tasks = []
            for url in urls:
                task = asyncio.create_task(
                    self._download_video(ydl, url, platform)
                )
                tasks.append(task)
            await asyncio.gather(*tasks)

    async def _download_video(self, ydl, url, platform):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, ydl.download, [url])
        self.videos.append(
            os.path.join(
                'videos',
                platform,
                ydl.prepare_filename(ydl.extract_info(url, download=False)),
            )
        )

    async def upload_to_vk(self, vk_login, vk_password, group_id):
        vk_session = VkApi(login=vk_login, password=vk_password)
        vk_session.auth()
        upload = VkUpload(vk_session)

        random.shuffle(self.videos)

        tasks = []
        for video in self.videos:
            task = asyncio.create_task(
                self._upload_video(upload, video, group_id)
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

    async def _upload_video(self, upload, video, group_id):
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                upload.video,
                video_file=video,
                group_id=group_id,
                name=os.path.basename(video),
                description='Auto uploaded video',
            )
        except VkApiError as e:
            print(f'Failed to upload {video} to VK: {e}')


async def main():
    downloader = VideoDownloaderAsync()

    # Вводим данные для авторизации и необходимые ссылки
    vk_login = 'your_vk_login'
    vk_password = 'your_vk_password'
    group_id = 'your_group_id'
    insta_username = 'your_insta_username'
    insta_password = 'your_insta_password'
    youtube_shorts_playlist = 'https://www.youtube.com/@cutpravda/shorts'

    # Скачиваем видео
    # await downloader.download_from_vkontakte(vk_login, vk_password)
    # await downloader.download_from_youtube(youtube_shorts_playlist)
    # await downloader.download_from_instagram(insta_username, insta_password)
    await downloader.download_from_tiktok()

    # Загружаем видео в группу ВКонтакте
    # await downloader.upload_to_vk(vk_login, vk_password, group_id)


if __name__ == '__main__':
    asyncio.run(main())
