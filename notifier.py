import aiohttp
import asyncio
from yarl import URL
import smtplib
from email.mime.text import MIMEText
from storage import myConfigParser

cf = myConfigParser()
cf.read('config.ini')

weixin_key = cf.get('notifier', 'weixin_key')
mail_host = cf.get('notifier', 'mail_host')
mail_user = cf.get('notifier', 'mail_user')
mail_pass = cf.get('notifier', 'mail_pass')
sender = cf.get('notifier', 'sender')
receivers = cf.get('notifier', 'receivers')


class Notifier:
    def __init__(self):
        self.notify = []

    def collect_notify(self, info):
        self.notify.append(info)

    def send_notify(self):
        if not self.notify:
            return
        self.send_notify_mail()
        self.send_notify_weixin()
        self.notify = []

    def send_notify_mail(self):
        if not mail_user and not mail_pass:
            raise UserWarning('Not Set Mail')
        content = '\n'.join(self.notify)
        message = MIMEText(content, 'plain', 'utf-8')
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
            print('Mail Send Success')
        except smtplib.SMTPException as e:
            print('Mail Send Error', e)

    def send_notify_weixin(self):
        if not weixin_key:
            raise UserWarning('Not Set Weixin')

        session = aiohttp.ClientSession()

        async def send(text, resp=None):
            url = URL('https://sc.ftqq.com/{weixin_key}.send'.format(weixin_key=weixin_key))
            data = {
                'text': text,
                'resp': resp
            }
            async with session.post(url=url, data=data) as response:
                json = await response.json(content_type='text/html;charset=utf-8')
                if json['errno'] != 0:
                    raise ConnectionError('WeiXin Send Error', json)

        tasks = []
        for notify in self.notify:
            tasks.append(send(notify))

        async def send_main():
            try:
                await asyncio.gather(*tasks)
            except ConnectionError as e:
                print('WeiXin Send Error', e.strerror)
            else:
                print('WeiXin Send Success')
            await session.close()

        loop = asyncio.get_event_loop()
        loop.create_task(send_main())


notifier = Notifier()
