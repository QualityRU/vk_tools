import vk_api

# Установите свои значения
group_id = 227048692  # ID группы, отрицательное число для идентификации группы
token = 'vk1.a.ZYcABHgEHDEXe1bl4YmFt8yFid_bi172xg3zgU7PfyfA2g1NexgkCh8zKzULBhqBbSOFPylVrwLWpLeMxq0fcFEX9RW3lABzBy062cyGXoxz-b_hp5mr5qPWUAGrddNru8NQJFFVcudMzJvmnLnFgWkieJx_QSvLZWb7FpzwDRo2ST1wf-_P8ny0sBvWvTyqZ0wVQ9SGDu7cs9NN-yLUBg'  # Токен с правами доступа к управлению группой

# Авторизация
vk_session = vk_api.VkApi(token=token)
vk = vk_session.get_api()

# Получаем все посты со стены группы
def get_all_posts(owner_id, count=200):
    offset = 0
    all_posts = []
    while True:
        posts = vk.wall.get(owner_id=owner_id, count=count, offset=offset)[
            'items'
        ]
        if not posts:
            break
        all_posts.extend(posts)
        offset += count
        print(offset)
    return all_posts


# Удаление всех постов
def delete_all_posts(owner_id):
    posts = get_all_posts(owner_id)
    for post in posts:
        vk.wall.delete(owner_id=owner_id, post_id=post['id'])
        print(f"Post {post['id']} deleted.")


delete_all_posts(owner_id=-group_id)
