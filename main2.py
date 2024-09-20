import asyncio
import traceback

from colorama import Fore

from core.logger import log
from core.utils import MethodDict, read_config
from core.vk import VKDownloader, VKUploader


async def download(vk, groups, cache_name, limit=5):
    log.info(Fore.YELLOW + 'Начинается загрузка...')
    urls = await vk.fetch_video_urls(groups, cache_name, limit)
    await asyncio.gather(*[vk.download_video(url, cache_name) for url in urls])
    log.info(Fore.GREEN + 'Загрузка завершена.')


async def upload(uploader, path, group, cache_name, desc):
    log.info(Fore.YELLOW + 'Начинается выгрузка...')
    await uploader.upload_videos(path, group, cache_name, desc, wallpost=1)
    log.info(Fore.GREEN + 'Выгрузка завершена.')


async def schedule(func, interval, *args):
    await func(*args)
    await asyncio.sleep(interval)
    await schedule(func, interval, *args)  # Рекурсивный вызов вместо цикла


async def main():
    cfg = MethodDict(await read_config('config.json'))
    tokens = cfg.groups.Девушки.accounts.tokens
    vk = VKDownloader(tokens=tokens)
    uploader = VKUploader(tokens=tokens)

    try:
        await asyncio.gather(
            schedule(
                download,
                3600,
                vk,
                cfg.groups.Девушки.groups_from_download,
                cfg.groups.Девушки.cache_name,
            ),
            schedule(
                upload,
                3600,
                uploader,
                'clips',
                cfg.groups.Девушки.group_to_upload,
                cfg.groups.Девушки.cache_name,
                cfg.groups.Девушки.group_description,
            ),
        )
    except Exception:
        log.error(Fore.RED + f'Ошибка: {traceback.format_exc()}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        log.error(Fore.RED + f'Произошла ошибка: {traceback.format_exc()}')
