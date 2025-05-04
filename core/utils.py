import json

import aiofiles


class MethodDict:
    def __init__(self, data=None):
        self._dict = self._convert_dict(data if data is not None else {})

    def _convert_dict(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = MethodDict(value)
        return data

    def __getattr__(self, name):
        if name in self._dict:
            return self._dict[name]
        raise AttributeError(f"'MethodDict' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._dict[name] = self._convert_dict({name: value})[name]

    def __delattr__(self, name):
        if name in self._dict:
            del self._dict[name]
        else:
            raise AttributeError(
                f"'MethodDict' object has no attribute '{name}'"
            )

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()


def read_config(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        content = file.read()
        config = json.loads(content)
    return config
