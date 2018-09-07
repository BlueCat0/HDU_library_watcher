import argparse
import asyncio
import logging.config
import os
import sys
from collections import namedtuple

import aiohttp
import lxml.html

import notifier as _notifier
import storage
from book import Book


def get_args():
    parser = argparse.ArgumentParser(description='Book Watcher')
    parser.add_argument('-s', '--shelf_number', required=True,
                        help='[REQUIRED]The class id of Book Shelf you watched.')
    parser.add_argument('-t', '--loop_time', type=int, default=3600,
                        help='Check loop interval [s]')

    parser.add_argument('-w', '--weixin_notify', action='store_true',
                        help='Notify with weixin')
    _weixin_notify = '-w' in sys.argv | '--weixin_notify' in sys.argv
    parser.add_argument('-wk', '--weixin_notify_key', required=_weixin_notify,
                        help='Get Weixin Notify Key from ServerChan')

    parser.add_argument('-m', '--mail_notify', action='store_true',
                        help='Notify with mail')
    _mail_notify = '-m' in sys.argv | '--mail_notify' in sys.argv
    parser.add_argument('-mh', '--mail_notify_host', required=_mail_notify,
                        help='SMTP mail host')
    parser.add_argument('-mu', '--mail_notify_user', required=_mail_notify,
                        help='SMTP mail username')
    parser.add_argument('-mp', '--mail_notify_pass', required=_mail_notify,
                        help='SMTP mail password')
    parser.add_argument('-ms', '--mail_notify_sender', required=_mail_notify,
                        help='SMTP mail sender')
    parser.add_argument('-mr', '--mail_notify_receiver', required=_mail_notify,
                        help='SMTP mail receiver')

    args = parser.parse_args()

    _weixin = _notifier.weixin(args.weixin_notify_key) \
        if _weixin_notify else None
    _mail = _notifier.mail(args.mail_notify_host, args.mail_notify_user, args.mail_notify_pass, args.mail_notify_sender,
                           args.mail_notify_receiver) \
        if _mail_notify else None

    return namedtuple('args', ['shelf_number', 'loop_time', 'weixin', 'mail'])(
        args.shelf_number, args.loop_time, _weixin, _mail
    )


def init_logger():
    try:
        logging.config.fileConfig('logging.ini')
    except FileNotFoundError:
        os.mkdir('log')
    logging.config.fileConfig('logging.ini')
    return logging.getLogger('Watcher')


async def fetch(session: aiohttp.ClientSession, book: Book):
    async with session.get(book.get_ajax_page_url()) as response:
        try:
            html = await response.text()
        except Exception as e:
            logger.warning('Unable to access web-page of {}'.format(book), exc_info=True)
            raise e
        else:
            logger.debug('Access {} page success \n {}'.format(book, html))
            parse_result = parse_html(html, book)
            return parse_result


def parse_html(html, book: Book):
    dom = lxml.html.fromstring(html)
    state_list = dom.xpath('//*[@id="item"]/tr/td[5]/font/text() | //*[@id="item"]/tr/td[5]/text()')
    state = '可借' not in state_list

    logger.debug('Parse {} result is {} {}'.format(book, state, state_list))
    return state


async def add_success_callback(book, callback):
    borrowed = await callback
    if book.borrowed != borrowed:
        logger.info('{} borrow state change'.format(book))
        book.borrowed = borrowed
        notifier.collect_notify(book)

    else:
        logger.debug('{} borrow state not change'.format(book))


async def check_loop(shelf: str, loop_time: int = 3600):
    logger.info('-----------------------')
    logger.info('Watcher start')

    session = aiohttp.ClientSession()
    try:
        while True:
            logger.info('Checking...')

            with storage.FLock():
                store = storage.load()
                logger.debug('Load {} stored book'.format(len(store)))

                futures = []
                for book in store:
                    future = fetch(session, book)
                    future = add_success_callback(book, future)
                    futures.append(future)
                await asyncio.gather(*futures)

                storage.dump(store)
                logger.debug('Store {} books to file'.format(len(store)))
            notifier.send_notify()

            logger.info('Wait for {}s'.format(loop_time))
            await asyncio.sleep(loop_time)
    except Exception as e:
        logger.error('Watcher occurs error', exc_info=True)
        raise e

    finally:
        session.close()
        logger.info('Watcher stop')
        logger.info('-----------------------')


args_tuple = get_args()
logger = init_logger()
notifier = _notifier.Notifier(args_tuple.mail, args_tuple.weixin, logger)

loop = asyncio.get_event_loop()
loop.run_until_complete(check_loop(args_tuple.shelf_number, args_tuple.loop_time))
