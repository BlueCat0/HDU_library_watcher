import asyncio
import logging
from collections import namedtuple
from email.mime.text import MIMEText

import aiohttp
import aiosmtplib
from yarl import URL

from .book import Book


class Notifier:
    Weixin = namedtuple('weixin', ['key'])
    Mail = namedtuple('mail', ['host', 'username', 'password', 'sender', 'receiver'])
    Notify = namedtuple('notify', ['book', 'message'])

    def __init__(self, weixin: Weixin = None, mail: Mail = None,
                 logger: logging.Logger = logging.getLogger('Watcher.Notifier')):
        self.notify_list = []  # type: [self.Notify]

        self.logger = logger
        self._weixin = weixin
        if self._weixin:
            self.logger.info('WeiXin notify init')

        self._mail = mail
        if self._mail:
            self.logger.info('Mail notify init')

    def collect_notify(self, book: Book, message):
        self.notify_list.append(self.Notify(book, message))

    async def send_all_status(self, books: [Book]):
        self.logger.debug('Send all status')
        _loop = asyncio.get_event_loop()
        if self._mail:
            _loop.create_task(self.send_notify_mail(books))
        if self._weixin:
            _loop.create_task(self.send_notify_weixin(books))

    async def send_notify(self):
        self.logger.debug('Notify list {}'.format(self.notify_list))
        if not self.notify_list:
            return
        _loop = asyncio.get_event_loop()
        if self._mail:
            _loop.create_task(self.send_notify_mail(self.notify_list.copy()))
        if self._weixin:
            _loop.create_task(self.send_notify_weixin(self.notify_list.copy()))

        self.notify_list = []

    @staticmethod
    def generate_mail_content(notify_list: [Notify]):
        yield '<table border="1">'
        for notify in notify_list:
            yield '<tr>'
            yield '<td><b>{}</b></td>'.format(notify.message or notify.book.get_state())
            yield '<td>{}</td>'.format(notify.book)
            yield '<td><a href=\'{}\'>详情页</a></td>'.format(str(notify.book.get_detail_page_url()))
            yield '</tr>'
        yield '</table>'

    async def send_notify_mail(self, notify_list: [Notify]):
        content = ''.join(self.generate_mail_content(notify_list))
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = '书籍监控变动'
        message['From'] = self._mail.sender
        message['To'] = self._mail.receiver
        try:
            smtp = aiosmtplib.SMTP(hostname='smtp.163.com', port=465, loop=asyncio.get_event_loop(), use_tls=True)
            await smtp.connect()
            await smtp.login(self._mail.username, self._mail.password)
            await smtp.sendmail(
                self._mail.sender, self._mail.receiver, message.as_string())
            await smtp.quit()

        except aiosmtplib.SMTPException and TimeoutError:
            self.logger.warning('Mail notify send error', exc_info=True)

        else:
            self.logger.debug('Mail notify send success')

    @staticmethod
    def generate_weixin_resp(notify_list: [Notify]):
        yield '| 状态 | 书籍 | 链接 |\n'
        yield '| ---- | ---- | ---- |\n'
        for notify in notify_list:
            yield '| **{}** | {} | [链接]({}) |\n'.format(notify.message or notify.book.can_be_borrowed(),
                                                        notify.book,
                                                        notify.book.get_detail_page_url())

    async def send_notify_weixin(self, notify_list: [Notify]):
        async with aiohttp.ClientSession() as session:
            url = URL('https://sc.ftqq.com/{weixin_key}.send'.format(weixin_key=self._weixin.key))
            data = {
                'text': '{}本书籍监控变动'.format(len(notify_list)),
                'desp': ''.join(self.generate_weixin_resp(notify_list))
            }

            async with session.post(url=url, data=data) as response:
                try:
                    json = await response.json(content_type='text/html;charset=utf-8')
                    if json['errno'] != 0:
                        raise ConnectionError('WeiXin send error', json)
                except ConnectionError:
                    self.logger.error('WeiXin notify send error', exc_info=True)
                else:
                    self.logger.debug('WeiXin notify send success')
