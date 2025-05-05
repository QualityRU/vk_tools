import asyncio
from traceback import format_exc

from colorama import Fore

from core.logger import log
from core.utils import MethodDict, read_config
from core.vk import VKDownloader, VKUploader


def config():
    return MethodDict(read_config('config.json'))


async def download(limit=5):
    cfg = config()
    for k, v in cfg.groups.items():
        token = v.accounts.token
        groups = v.groups_from_download
        cache_name = v.cache_name

        downloader = VKDownloader(token=token)

        log.info(Fore.YELLOW + f'[{cache_name}] Начинается загрузка...')
        urls = await downloader.fetch_video_urls(groups, cache_name, limit)
        await asyncio.gather(
            *[downloader.download_video(url, cache_name) for url in urls]
        )
        log.info(Fore.GREEN + f'[{cache_name}] Загрузка завершена.')


async def upload():
    cfg = config()
    for k, v in cfg.groups.items():
        token = v.accounts.token
        cache_name = v.cache_name
        path = 'clips'
        group = v.group_to_upload
        cache_name = v.cache_name
        desc = v.group_description

        uploader = VKUploader(token=token)

        log.info(Fore.YELLOW + f'[{cache_name}] Начинается выгрузка...')
        await uploader.upload_videos(path, group, cache_name, desc, wallpost=1)
        log.info(Fore.GREEN + f'[{cache_name}] Выгрузка завершена.')


async def schedule(func, interval, *args):
    await func(*args)
    await asyncio.sleep(interval)
    await schedule(func, interval, *args)


async def main():
    try:
        await asyncio.gather(
            schedule(func=download, interval=18000),
            schedule(func=upload, interval=18000),
        )
    except Exception:
        log.error(Fore.RED + f'Ошибка: {format_exc()}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        log.error(Fore.RED + f'Произошла ошибка: {format_exc()}')
