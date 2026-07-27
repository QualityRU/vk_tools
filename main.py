import asyncio
import os
from traceback import format_exc

from colorama import Fore

from core.logger import log
from core.utils import MethodDict, read_config
from core.vk import VKDownloader, VKUploader


def config():
    return MethodDict(read_config('config.json'))


async def download_and_upload(limit=5):
    cfg = config()
    for _, v in cfg.groups.items():
        token = v.accounts.token
        groups = v.groups_from_download
        cache_name = v.cache_name
        group_to_upload = v.group_to_upload
        description = v.group_description

        downloader = VKDownloader(token=token)
        uploader = VKUploader(token=token)

        try:
            log.info(Fore.YELLOW + f'[{cache_name}] Начинается обработка...')
            target_group = await uploader.get_group_id_and_name(group_to_upload)
            if target_group is None:
                continue

            await uploader.upload_videos(
                'clips', group_to_upload, cache_name, description, wallpost=1
            )
            urls = await downloader.fetch_video_urls(groups, cache_name, limit)
            for video_url, cache_key in urls:
                video_path = await downloader.download_video(
                    video_url, cache_name, cache_key
                )
                if video_path is None:
                    continue

                success = await uploader.upload_clip(
                    abs(target_group[0]), video_path, description, wallpost=1
                )
                if success:
                    os.remove(video_path)
                else:
                    log.warning(
                        Fore.YELLOW
                        + f'[{cache_name}] Файл сохранён для повторной выгрузки: '
                        + video_path
                    )
                await asyncio.sleep(5)
            log.info(Fore.GREEN + f'[{cache_name}] Обработка завершена.')
        except Exception:
            log.error(
                Fore.RED + f'[{cache_name}] Ошибка обработки:\n{format_exc()}'
            )


async def schedule(func, interval, *args):
    while True:
        await func(*args)
        await asyncio.sleep(interval)


async def main():
    cfg = config()
    try:
        await asyncio.gather(
            schedule(func=download_and_upload, interval=cfg.UPDATE_SEC),
        )
    except Exception:
        log.error(Fore.RED + f'Ошибка: {format_exc()}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        log.error(Fore.RED + f'Произошла ошибка: {format_exc()}')
