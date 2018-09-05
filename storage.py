import json
import os
import time
from book import Book
import configparser

path = 'book.json'


class myConfigParser(configparser.ConfigParser):
    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, optionstr):
        return optionstr


class FLock:
    def __init__(self, block=True):
        self.block = block

    def __enter__(self):
        if self.block:
            while True:
                if not os.path.exists('LOCK'):
                    break
                print('wait')
        else:
            if os.path.exists('LOCK'):
                raise BlockingIOError
        open('LOCK', 'w').close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.remove('LOCK')


def dump(store):
    with FLock():
        with open(path, 'w') as f:
            json.dump(store, f, default=Book.serialize)


def load():
    with FLock():
        try:
            with open(path, 'r') as f:
                store = json.load(f, object_hook=Book.deserialization)
        except FileNotFoundError:
            store = []
    return store
