import argparse
import json
import storage
import asyncio
import aiohttp
import lxml.html
from book import Book
from yarl import URL


async def create_book_main(_add_list):
    session = aiohttp.ClientSession()
    futures = [create_book(session, _marc_no) for _marc_no in _add_list]
    results = await asyncio.gather(*futures)
    await session.close()
    return results


async def create_book(session: aiohttp.ClientSession, _marc_no):
    url = URL('http://210.32.33.91:8080/opac/item.php').with_query(marc_no=_marc_no)
    async with session.get(url) as response:
        html = await response.text()
        book = Book(*parse_html(html), _marc_no)
        return book


def parse_html(html):
    dom = lxml.html.fromstring(html)
    title = ''.join(dom.xpath('//*[@id="item_detail"]/dl[1]/dd/a/text()'))
    author = ''.join(dom.xpath('//*[@id="item_detail"]/dl[1]/dd/text()'))
    author = author[1:]
    publishing_issue = ''.join(dom.xpath('//*[@id="item_detail"]/dl[2]/dd/text()'))
    return title, author, publishing_issue


def main():
    parser = argparse.ArgumentParser(description='Manage your watched book')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--ls', dest='ls', action='store_true', help='List books watched')
    group.add_argument('-a', '--add', dest='to_add', nargs='+', action='store', help='Add books want to be watched')
    group.add_argument('-d', '--del', dest='to_del', nargs='+', action='store', help='Del books watched')
    args = parser.parse_args()

    store = storage.load()
    if args.ls:
        for book in store:
            print(book)

    if args.to_add:
        for marc_no in args.to_add:
            tmp_book = Book('t', 't', 't', marc_no)
            if tmp_book in store:
                args.to_add.remove(marc_no)
        to_add = set(args.to_add)
        loop = asyncio.get_event_loop()
        to_add_books = loop.run_until_complete(create_book_main(to_add))
        store += to_add_books
        storage.dump(store)

    if args.to_del:
        for marc_no in args.to_del:
            tmp_book = Book('t', 't', 't', marc_no)
            if tmp_book in store:
                store.remove(tmp_book)
            else:
                raise UserWarning('Not Found Book You Want To Del')
        storage.dump(store)




main()
