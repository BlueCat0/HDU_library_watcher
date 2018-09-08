import json
import os
import time
import typing

from .book import Book

path = 'book.json'


class FLock:
    def __init__(self, block=True):
        self.block = block

    def __enter__(self):
        if self.block:
            while True:
                if not os.path.exists('LOCK'):
                    break
                print('wait for lock')
                time.sleep(1)
        else:
            if os.path.exists('LOCK'):
                raise BlockingIOError
        open('LOCK', 'w').close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove('LOCK')


def dump(store: typing.Dict[str, 'Book']):
    with open(path, 'w') as f:
        json.dump(store, f, default=Book.serialize)


def load() -> typing.Dict[str, 'Book']:
    try:
        with open(path, 'r') as f:
            store = json.load(f, object_hook=Book.deserialization)
    except FileNotFoundError:
        store = {}
    return store
