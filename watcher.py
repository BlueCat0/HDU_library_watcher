import aiohttp
import asyncio
from yarl import URL
from book import Book
import storage
import lxml.html
import notifier

notifier = notifier.notifier


async def fetch(session: aiohttp.ClientSession, marc_no):
    url = URL('http://210.32.33.91:8080/opac/ajax_item.php').with_query({'marc_no': marc_no})
    async with session.get(url) as response:
        html = await response.text()
    return parse_html(html)


def parse_html(html):
    dom = lxml.html.fromstring(html)
    state_list = dom.xpath('//*[@id="item"]/tr/td[5]/text()')
    return '可借' in state_list


def notify(book: Book):
    text = '《{title}》处于{borrowed}状态'.format(title=book.title, borrowed='借出' if book.borrowed else '可借')
    print(text)
    notifier.collect_notify(text)


async def add_success_callback(book, callback):
    un_borrowed = await callback
    if book.borrowed == un_borrowed:
        if un_borrowed:
            book.borrowed = False
        else:
            book.borrowed = True
        notify(book)


async def main():
    session = aiohttp.ClientSession()
    try:
        while True:
            print('Checking...')

            store = storage.load()
            futures = []
            for book in store:
                future = fetch(session, book.marc_no)
                future = add_success_callback(book, future)
                futures.append(future)
            await asyncio.gather(*futures)
            storage.dump(store)
            notifier.send_notify()

            print('Waiting...')
            await asyncio.sleep(600)
    finally:
        session.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
