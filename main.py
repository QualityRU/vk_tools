import asyncio
import traceback

from colorama import Fore

from core.logger import log
from core.utils import MethodDict, read_config
from core.vk import VKDownloader, VKUploader


async def config():
    return MethodDict(await read_config('config.json'))


async def download(limit=5):
    cfg = await config()
    token = cfg.groups.Автогараж.accounts.token
    downloader = VKDownloader(token=token)
    groups = cfg.groups.Автогараж.groups_from_download
    cache_name = cfg.groups.Автогараж.cache_name

    log.info(Fore.YELLOW + 'Начинается загрузка...')
    urls = await downloader.fetch_video_urls(groups, cache_name, limit)
    await asyncio.gather(
        *[downloader.download_video(url, cache_name) for url in urls]
    )
    log.info(Fore.GREEN + 'Загрузка завершена.')


async def upload():
    cfg = await config()
    token = cfg.groups.Автогараж.accounts.token
    uploader = VKUploader(token=token)
    path = 'clips'
    group = cfg.groups.Автогараж.group_to_upload
    cache_name = cfg.groups.Автогараж.cache_name
    desc = cfg.groups.Автогараж.group_description

    log.info(Fore.YELLOW + 'Начинается выгрузка...')
    await uploader.upload_videos(path, group, cache_name, desc, wallpost=1)
    log.info(Fore.GREEN + 'Выгрузка завершена.')


async def schedule(func, interval, *args):
    await func(*args)
    await asyncio.sleep(interval)
    await schedule(func, interval, *args)


async def main():
    try:
        await asyncio.gather(
            schedule(func=download, interval=3600),
            schedule(func=upload, interval=3600),
        )
    except Exception:
        log.error(Fore.RED + f'Ошибка: {traceback.format_exc()}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        log.error(Fore.RED + f'Произошла ошибка: {traceback.format_exc()}')
