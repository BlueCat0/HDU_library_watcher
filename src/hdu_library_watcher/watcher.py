import argparse
import asyncio
import logging.config
import os
import sys
import typing
from collections import namedtuple

import aiohttp
import lxml.html
from yarl import URL

from src.hdu_library_watcher import notifier as _notifier, storage
from src.hdu_library_watcher.book import Book


def get_args():
    parser = argparse.ArgumentParser(description='Book Watcher')
    parser.add_argument('-s', '--shelf_number', required=True,
                        help='[REQUIRED]The class id of Book Shelf you watched.')
    parser.add_argument('-t', '--loop_time', type=int, default=3600,
                        help='Check loop interval [s]')

    parser.add_argument('-w', '--weixin_notify', action='store_true',
                        help='Notify with weixin')
    _weixin_notify = ('-w' in sys.argv) | ('--weixin_notify' in sys.argv)
    parser.add_argument('-wk', '--weixin_notify_key', required=_weixin_notify,
                        help='Get Weixin Notify Key from ServerChan')

    parser.add_argument('-m', '--mail_notify', action='store_true',
                        help='Notify with mail')
    _mail_notify = ('-m' in sys.argv) | ('--mail_notify' in sys.argv)
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

    _weixin = _notifier.Weixin(args.weixin_notify_key) \
        if _weixin_notify else None
    _mail = _notifier.Mail(args.mail_notify_host, args.mail_notify_user, args.mail_notify_pass, args.mail_notify_sender,
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


async def get_shelf_books(session: aiohttp.ClientSession, shelf: str) -> typing.Dict[str, 'Book']:
    async def create_book_from_book_bom(book_bom: lxml.html.Element) -> Book:
        title = ''.join(book_bom.xpath('td[2]/a/text()'))
        author = ''.join(book_bom.xpath('td[3]/text()'))
        publisher = ''.join(book_bom.xpath('td[4]/text()'))
        publish_date = ''.join(book_bom.xpath('td[5]/text()'))
        call_no = ''.join(book_bom.xpath('td[6]/text()'))
        marc_no_url = URL(''.join(book_bom.xpath('td[2]/a/@href')))
        marc_no = marc_no_url.query.get('marc_no')
        state = await get_book_state(session, marc_no)
        return Book(title, author, publisher, publish_date, call_no, marc_no, state)

    url = URL('http://210.32.33.91:8080/opac/show_user_shelf.php').with_query(classid=shelf)
    async with session.get(url) as response:
        try:
            html = await response.text()
        except Exception as e:
            logger.debug('Unable to access shelf {} page'.format(shelf), exc_info=True)
            raise e
        else:
            logger.debug('Access {} shelf page success'.format(shelf))

            bom = lxml.html.fromstring(html)
            book_bom_list = bom.xpath('//*[@id="container"]/table/tr')[1:]

            _loop = asyncio.get_event_loop()
            book_tasks = [_loop.create_task(create_book_from_book_bom(book_bom)) for book_bom in book_bom_list]
            finished, unfinished = await asyncio.wait(book_tasks)

            book_dict = {}  # type: typing.Dict[str, 'Book']
            for r in finished:
                book = r.result()
                if not isinstance(book, Book):
                    raise TypeError('{} is not a Book Object', )
                book_dict[book.call_no] = book
            logger.debug('shelf book is {}'.format(book_dict))
            return book_dict


async def get_book_state(session: aiohttp.ClientSession, marc_no: str):
    url = URL('http://210.32.33.91:8080/opac/ajax_item.php').with_query(marc_no=marc_no)
    async with session.get(url) as response:
        try:
            html = await response.text()
        except Exception as e:
            logger.warning('Unable to access ajax-page of {}'.format(marc_no), exc_info=True)
            raise e
        else:
            logger.debug('Access {} ajax-page success'.format(marc_no))
            dom = lxml.html.fromstring(html)
            state_list = dom.xpath('//*[@id="item"]/tr/td[5]/font/text() | //*[@id="item"]/tr/td[5]/text()')
            state = '可借' in state_list
            logger.debug('Parse {} result is {} {}'.format(marc_no, state, state_list))
            return state


async def check_loop(shelf: str, loop_time: int = 3600):
    logger.info('-----------------------')
    logger.info('Watcher start')

    session = aiohttp.ClientSession()
    try:
        while True:
            try:
                logger.info('Checking...')

                books = await get_shelf_books(session, shelf)  # type: typing.Dict[str, 'Book']
                logger.debug('Get {} shelf books'.format(len(books)))

                with storage.FLock():
                    store_books = storage.load()  # type: typing.Dict[str, 'Book']
                    logger.debug('Load {} stored books'.format(len(store_books)))

                    for call_no, store_book in store_books.items():
                        if store_book not in books.values():
                            logger.info('Stop track {}'.format(store_book))
                            notifier.collect_notify(store_book, '停止追踪')
                            del store_books[call_no]

                    for call_no, book in books.items():
                        if book not in store_books.values():
                            logger.info('Begin track {}'.format(book))
                            notifier.collect_notify(book, '开始追踪')
                            store_books[call_no] = book
                        else:
                            if book.state != store_books.get(call_no).state:
                                logger.info('Tracked book {} state change'.format(book))
                                notifier.collect_notify(book, None)
                                store_books[call_no] = book
                            else:
                                logger.debug('Tracked book {} state not change'.format(book))

                    storage.dump(store_books)
                    logger.debug('Store {} books to file'.format(len(store_books.values())))

                await notifier.send_notify()

            except TimeoutError:
                logger.error('Watcher occurs error', exc_info=True)

            except Exception as e:
                logger.error('Watcher occurs error', exc_info=True)
                raise e

            finally:
                logger.info('Wait for {}s'.format(loop_time))
                await asyncio.sleep(loop_time)

    finally:
        await session.close()
        logger.info('Watcher stop')
        logger.info('-----------------------')

args_tuple = get_args()
logger = init_logger()
notifier = _notifier.Notifier(mail=args_tuple.mail, weixin=args_tuple.weixin)

loop = asyncio.get_event_loop()
loop.run_until_complete(check_loop(shelf=args_tuple.shelf_number, loop_time=args_tuple.loop_time))
