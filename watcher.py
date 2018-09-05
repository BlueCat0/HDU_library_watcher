import asyncio

import aiohttp
import lxml.html

import logger as _logger
import notifier
import storage
from book import Book

logger = _logger.logger

notifier = notifier.notifier


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


async def main():
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

            logger.info('Wait for 1800s')
            await asyncio.sleep(1800)
    except Exception as e:
        logger.error('Watcher occurs error', exc_info=True)
        raise e

    finally:
        session.close()
        logger.info('Watcher stop')


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
