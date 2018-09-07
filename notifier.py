import asyncio
import logging
import smtplib
from collections import namedtuple
from email.mime.text import MIMEText

import aiohttp
from yarl import URL

from book import Book

weixin = namedtuple('weixin', ['key'])
mail = namedtuple('mail', ['host', 'username', 'password', 'sender', 'receiver'])


class Notifier:
    def __init__(self, _weixin: weixin = None, _mail: mail = None,
                 logger: logging.Logger = logging.getLogger('Watcher.Notifier')):
        self.notify_list = []  # type: [Book]

        self.logger = logger
        self._weixin = _weixin
        if self._weixin:
            self.logger.info('WeiXin notify init')

        self._mail = _mail
        if self._mail:
            self.logger.info('Mail notify init')

    def collect_notify(self, book: Book):
        self.notify_list.append(book)

    @staticmethod
    def generate_mail_content(books):
        yield '<table border="1">'
        for book in books:
            yield '<tr>'
            yield '<td><b>{}</b></td>'.format(book.can_be_borrowed())
            yield '<td>{}</td>'.format(book)
            yield '<td><a href=\'{}\'>详情页</a></td>'.format(str(book.get_detail_page_url()))
            yield '</tr>'
        yield '</table>'

    def send_notify(self):
        if not self.notify_list:
            return
        if self._mail:
            self.send_notify_mail()
        if self._weixin:
            self.send_notify_weixin()
        self.notify_list = []

    def send_notify_mail(self):
        content = ''.join(self.generate_mail_content(self.notify_list))
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = '书籍监控变动'
        message['From'] = self._mail.sender
        message['To'] = self._mail.receiver

        try:
            smtp_obj = smtplib.SMTP_SSL(self._mail.host, 465)
            smtp_obj.login(self._mail.username, self._mail.password)
            smtp_obj.sendmail(
                self._mail.sender, self._mail.receiver, message.as_string())
            smtp_obj.quit()
            self.logger.info('Mail notify send success')
            self.logger.debug('Mail content is %s', content)

        except smtplib.SMTPException and TimeoutError:
            self.logger.warning('Mail notify send error', exc_info=True)

    @staticmethod
    def generate_weixin_resp(books: [Book]):
        yield '| 状态 | 书籍 | 链接 |\n'
        yield '| ---- | ---- | ---- |\n'
        for book in books:
            yield '| **{}** | {} | [链接]({}) |\n'.format(book.can_be_borrowed(),
                                                        book,
                                                        book.get_detail_page_url())

    def send_notify_weixin(self):
        session = aiohttp.ClientSession()

        async def send(text, desp=None):
            url = URL('https://sc.ftqq.com/{weixin_key}.send'.format(weixin_key=self._weixin.key))
            data = {
                'text': text,
                'desp': desp
            }
            async with session.post(url=url, data=data) as response:
                json = await response.json(content_type='text/html;charset=utf-8')
                if json['errno'] != 0:
                    raise ConnectionError('WeiXin Send Error', json)

        task = send(
            text='{}本书籍监控变动'.format(len(self.notify_list)),
            desp=''.join(self.generate_weixin_resp(self.notify_list))
        )

        async def send_main():
            try:
                await asyncio.gather(task)
            except ConnectionError:
                self.logger.error('WeiXin Send Error', exc_info=True)
            else:
                self.logger.info('WeiXin Send Success')
            await session.close()

        loop = asyncio.get_event_loop()
        loop.create_task(send_main())
