import os

cache_dir = 'cache'
clips_dir = 'clips'
result_dir = 'result'

os.makedirs(result_dir, exist_ok=True)


def get_numbers_from_txt(filepath):
    with open(filepath, 'r') as file:
        return {line.strip() for line in file if line.strip().isdigit()}


def get_numbers_from_clips(cache_dir, clips_dir, result_dir):
    file_cache_set = {
        filename[:-4]
        for filename in os.listdir(cache_dir)
        if filename.endswith('.txt')
    }
    dir_clip_set = {
        item[7:]
        for item in os.listdir(clips_dir)
        if item.startswith('Группа_')
    }
    common_dirs = file_cache_set & dir_clip_set

    for d in common_dirs:
        cache_list = get_numbers_from_txt(f'{cache_dir}/{d}.txt')
        clip_files = [
            f.split('.')[0]
            for f in os.listdir(f'{clips_dir}/Группа_{d}')
            if f.endswith('.mp4') and f.split('.')[0].isdigit()
        ]
        diff_set = cache_list.symmetric_difference(clip_files)

        with open(f'{result_dir}/{d}.txt', 'w') as file:
            file.write('\n'.join(diff_set) + '\n')


if __name__ == '__main__':
    get_numbers_from_clips(cache_dir, clips_dir, result_dir)
