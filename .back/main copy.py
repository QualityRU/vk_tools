import asyncio
import concurrent.futures
import traceback

from colorama import Fore

from core.downloader import VKDownloader
from core.logger import log
from core.uploader import VKUploader
from core.utils import MethodDict, read_config


async def main():
    config = MethodDict(await read_config('config.json'))

    tokens = config.groups.Автогараж.accounts.tokens
    login = config.groups.Автогараж.accounts.login
    password = config.groups.Автогараж.accounts.password
    group_to_upload = config.groups.Автогараж.group_to_upload
    groups_from_download = config.groups.Автогараж.groups_from_download
    proxies = []  # Или await downloader.read_proxies('proxies.txt')

    if not groups_from_download:
        log.error(Fore.RED + 'Нет ссылок на группы.')
        return

    num_threads = len(groups_from_download)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=num_threads
    ) as executor:
        loop = asyncio.get_running_loop()
        tasks = []

        for group_link in groups_from_download:
            downloader = VKDownloader(login=None, password=None, tokens=tokens)

            downloader_task = loop.run_in_executor(
                executor,
                lambda: asyncio.run(
                    downloader.download_videos_from_group(group_link)
                ),
            )
            tasks.append(downloader_task)

            # uploader = VKUploader(login=None, password=None, tokens=tokens)
            # upload_task = loop.run_in_executor(
            #     executor,
            #     lambda: asyncio.run(uploader.upload_videos(save_dir)),
            # )
            # tasks.append(upload_task)

        await asyncio.gather(*tasks)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        log.error(Fore.RED + f'Произошла ошибка: {traceback.format_exc()}')
