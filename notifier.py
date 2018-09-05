import asyncio
import smtplib
from email.mime.text import MIMEText

import aiohttp
from yarl import URL

import logger as _logger
from book import Book
from storage import MyConfigParser

logger = _logger.logger

cf = MyConfigParser()
cf.read('config.ini')

weixin = cf.getboolean('notifier', 'weixin')
weixin_key = cf.get('notifier', 'weixin_key')

mail = cf.getboolean('notifier', 'mail')
mail_host = cf.get('notifier', 'mail_host')
mail_user = cf.get('notifier', 'mail_user')
mail_pass = cf.get('notifier', 'mail_pass')
sender = cf.get('notifier', 'sender')
receivers = cf.get('notifier', 'receivers')

if weixin:
    logger.info('Init WeiXin notify')

if mail:
    logger.info('Init Mail notify')


class Notifier:
    def __init__(self):
        self.notify = []  # type: [Book]

    def collect_notify(self, book: Book):
        self.notify.append(book)

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
        if not self.notify:
            return
        if mail:
            self.send_notify_mail()
        if weixin:
            self.send_notify_weixin()
        self.notify = []

    def send_notify_mail(self):
        if not mail_user and not mail_pass:
            raise UserWarning('Not Set Mail')
        content = ''.join(self.generate_mail_content(self.notify))
        message = MIMEText(content, 'html', 'utf-8')
        message['Subject'] = '书籍监控变动'
        message['From'] = sender
        message['To'] = receivers[0]

        try:
            smtp_obj = smtplib.SMTP()
            smtp_obj.connect(mail_host, 25)
            smtp_obj.login(mail_user, mail_pass)
            smtp_obj.sendmail(
                sender, receivers, message.as_string())
            smtp_obj.quit()
            logger.info('Mail Send Success, notify {} changes'.format(len(self.notify)))
            logger.debug('Mail Content is %s', content)

        except smtplib.SMTPException:
            logger.warning('Mail Send Error', exc_info=True)

    @staticmethod
    def generate_weixin_resp(books: [Book]):
        yield '| 状态 | 书籍 | 链接 |\n'
        yield '| ---- | ---- | ---- |\n'
        for book in books:
            yield '| **{}** | {} | [链接]({}) |\n'.format(book.can_be_borrowed(),
                                                        book,
                                                        book.get_detail_page_url())

    def send_notify_weixin(self):
        if not weixin_key:
            raise UserWarning('Not Set Weixin')

        session = aiohttp.ClientSession()

        async def send(text, desp=None):
            url = URL('https://sc.ftqq.com/{weixin_key}.send'.format(weixin_key=weixin_key))
            data = {
                'text': text,
                'desp': desp
            }
            async with session.post(url=url, data=data) as response:
                json = await response.json(content_type='text/html;charset=utf-8')
                if json['errno'] != 0:
                    raise ConnectionError('WeiXin Send Error', json)

        task = send(
            text='{}本书籍监控变动'.format(len(self.notify)),
            desp=''.join(self.generate_weixin_resp(self.notify))
        )

        async def send_main():
            try:
                await asyncio.gather(task)
            except ConnectionError:
                logger.error('WeiXin Send Error', exc_info=True)
            else:
                logger.info('WeiXin Send Success')
            await session.close()

        loop = asyncio.get_event_loop()
        loop.create_task(send_main())


notifier = Notifier()
