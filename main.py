import asyncio
import os
import random
import traceback
from concurrent.futures import ThreadPoolExecutor

from colorama import Fore

from core.logger import log
from core.utils import MethodDict, read_config
from core.vk_downloader import VKDownloader
from core.vk_uploader import VKUploader


async def download_videos_from_groups(groups_from_download, tokens):
    loop = asyncio.get_running_loop()
    num_threads = len(groups_from_download)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        tasks = [
            loop.run_in_executor(
                executor,
                lambda group_link=group_link: asyncio.run(
                    VKDownloader(
                        login=None, password=None, tokens=tokens
                    ).download_videos_from_group(group_link)
                ),
            )
            for group_link in groups_from_download
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            print(Fore.RED + 'Скачивание видео было отменено.')
        except Exception as e:
            log.error(
                Fore.RED
                + f'Ошибка при скачивании видео: {traceback.format_exc()}'
            )


async def periodic_download(groups_from_download, tokens, interval=3600):
    while True:
        print(Fore.YELLOW + 'Начинается скачивание видео из групп...')
        await download_videos_from_groups(groups_from_download, tokens)
        print(
            Fore.GREEN
            + 'Скачивание видео завершено. Ожидание следующего запуска...'
        )
        await asyncio.sleep(interval)


async def periodic_upload(
    uploader, clips_path, group_to_upload, description='', interval=1350
):
    while True:
        folders_with_mp4 = [
            f.path
            for f in os.scandir(clips_path)
            if f.is_dir()
            and any(file.endswith('.mp4') for file in os.listdir(f.path))
        ]

        all_video_files = [
            os.path.join(folder, f)
            for folder in folders_with_mp4
            for f in os.listdir(folder)
            if f.endswith('.mp4')
        ]

        if not all_video_files:
            break

        random_video_files = random.sample(
            all_video_files, min(5, len(all_video_files))
        )

        print(Fore.YELLOW + 'Начинается загрузка клипов...')
        try:
            await uploader.upload_videos(
                random_video_files, group_to_upload, description
            )
            print(Fore.GREEN + 'Загрузка клипов завершена.')
        except asyncio.CancelledError:
            print(Fore.RED + 'Загрузка клипов была отменена.')
        except Exception as e:
            log.error(
                Fore.RED
                + f'Ошибка при загрузке клипов: {traceback.format_exc()}'
            )

        print(
            Fore.YELLOW + 'Ожидание следующего часа перед загрузкой клипов...'
        )
        await asyncio.sleep(interval)


async def main():
    config = MethodDict(await read_config('config.json'))

    tokens = config.groups.Автогараж.accounts.tokens
    group_to_upload = config.groups.Автогараж.group_to_upload
    group_description = config.groups.Автогараж.group_description
    groups_from_download = config.groups.Автогараж.groups_from_download

    if not groups_from_download:
        log.error(Fore.RED + 'Нет ссылок на группы.')
        return

    uploader = VKUploader(login=None, password=None, tokens=tokens)
    clips_path = 'clips'
    download_task = asyncio.create_task(
        periodic_download(groups_from_download, tokens)
    )
    upload_task = asyncio.create_task(
        periodic_upload(
            uploader, clips_path, group_to_upload, group_description
        )
    )

    try:
        await asyncio.gather(download_task, upload_task)
        # await asyncio.gather(download_task)
        # # await asyncio.gather(upload_task)
    except asyncio.CancelledError:
        print(Fore.RED + 'Основные задачи были отменены.')
    except Exception as e:
        log.error(
            Fore.RED + f'Ошибка в основной программе: {traceback.format_exc()}'
        )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        log.error(Fore.RED + f'Произошла ошибка: {traceback.format_exc()}')
