import asyncio
import traceback

from colorama import Fore

from core.logger import log
from core.utils import MethodDict, read_config
from core.vk import VKDownloader, VKUploader


async def download(vk, group, cache_name, limit=5):
    log.info(Fore.YELLOW + f'Начинается загрузка для группы {cache_name}...')
    urls = await vk.fetch_video_urls(group, cache_name, limit)
    await asyncio.gather(*[vk.download_video(url, cache_name) for url in urls])
    log.info(Fore.GREEN + f'Загрузка для группы {cache_name} завершена.')


async def upload(uploader, path, group, cache_name, desc):
    log.info(Fore.YELLOW + f'Начинается выгрузка для группы {cache_name}...')
    await uploader.upload_videos(path, group, cache_name, desc)
    log.info(Fore.GREEN + f'Выгрузка для группы {cache_name} завершена.')


async def schedule(func, interval, *args):
    await func(*args)
    await asyncio.sleep(interval)
    await schedule(func, interval, *args)  # Рекурсивный вызов вместо цикла


async def process_group(vk, uploader, group_cfg):
    """Запускает задачи для одной группы."""
    try:
        await asyncio.gather(
            schedule(
                download,
                3600,
                vk,
                group_cfg.groups_from_download,
                group_cfg.cache_name,
            ),
            schedule(
                upload,
                3600,
                uploader,
                'clips',
                group_cfg.group_to_upload,
                group_cfg.cache_name,
                group_cfg.group_description,
            ),
        )
    except Exception:
        log.error(Fore.RED + f'Ошибка при обработке группы {group_cfg.cache_name}: {traceback.format_exc()}')


async def main():
    cfg = MethodDict(await read_config('config.json'))
    tokens = cfg.groups.Автогараж.accounts.tokens
    vk = VKDownloader(tokens=tokens)
    uploader = VKUploader(tokens=tokens)

    # Обрабатываем каждую группу в cfg.groups
    group_tasks = []
    for group_name, group_cfg in cfg.groups.items():
        group_tasks.append(process_group(vk, uploader, group_cfg))
    try:
        # Запускаем задачи для всех групп
        await asyncio.gather(*group_tasks)
    except Exception:
        log.error(Fore.RED + f'Произошла ошибка: {traceback.format_exc()}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception:
        log.error(Fore.RED + f'Произошла ошибка: {traceback.format_exc()}')
