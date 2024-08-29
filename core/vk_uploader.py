import asyncio
import os
import random
from os.path import getsize

import aiohttp
from colorama import Fore, init

from core.vkapi import VKAPI

init(autoreset=True)


class VKUploader(VKAPI):
    async def upload_clip(self, group_upload_id, video_path, description=''):
        try:
            if not self.vk_session:
                await self.get_vk_api()

            a = self.vk_session.shortVideo.create(
                group_id=group_upload_id,
                v=5.241,
                wallpost=1,
                description=description,
                file_size=getsize(video_path),
            )
            upload_url = a['upload_url']
            data = {'file': open(video_path, 'rb')}

            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, data=data) as res:
                    response_text = await res.text()
                    if (
                        res.status == 200
                        and response_text == '<retval>1</retval>'
                    ):
                        print(Fore.CYAN + f'Клип {video_path} успешно залит!')
                    elif (
                        res.status == 200 and 'Flood control' in response_text
                    ):
                        print(
                            Fore.RED
                            + 'Превышен лимит запросов. Повторная попытка через час.'
                        )
                        return False
                    else:
                        print(
                            Fore.RED
                            + f'Клип {video_path} не залит! Ответ: {response_text}'
                        )
                        return False

        except Exception as e:
            print(Fore.RED + f'Ошибка загрузки: {e}')
            return False

        return True

    async def upload_videos(
        self, random_video_files, group_upload, description
    ):
        group_upload_id = abs(await self.get_group_id_and_name(group_upload))

        while random_video_files:
            video_file = random_video_files.pop(0)
            success = await self.upload_clip(
                group_upload_id, video_file, description
            )
            if success:
                os.remove(video_file)
            else:
                print(Fore.YELLOW + 'Ожидание перед повторной попыткой...')
                await asyncio.sleep(900)

            await asyncio.sleep(5)
