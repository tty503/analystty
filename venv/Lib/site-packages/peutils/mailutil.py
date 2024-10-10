# -*- coding: UTF-8 -*-

'''
Author: Henry Wang
Date: 2022-01-19 13:58
Short Description:

Change History:

'''

import smtplib
import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText





class SendEmail:
    def __init__(self,name,pwd):
        self.name = name
        self.pwd = pwd


    def send_email(self, receiver, cc, content, subject=''):
        SENDER = self.name# 邮箱名
        SENDERNAME ="APPEN CS"
        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = email.utils.formataddr((SENDERNAME, SENDER))
        msg['to'] = ",".join(receiver)
        msg['Cc'] = ",".join(cc)
        USERNAME_SMTP = self.name # 带有邮件权限的 IAM 帐号
        PASSWORD_SMTP = self.pwd# 带有邮件权限的 IAM 密码
        HOST = "smtpdm.aliyun.com"
        PORT = 80

        thebody = MIMEText(content, 'html', 'utf-8')
        msg.attach(thebody)

        try:
            server = smtplib.SMTP(HOST, PORT)
            #server.ehlo()
            server.starttls()
            #server.ehlo()
            server.login(USERNAME_SMTP, PASSWORD_SMTP)
            server.sendmail(SENDER, receiver + cc, msg.as_string())
            server.close()
        except Exception as e:
            print("Error: ", e)


s = SendEmail(name="xxx",pwd="xxx")
s.send_email(receiver = ["hwang2@appen.com","yazhang@appen.com"],cc=[],subject="邮件标题",content="邮件内容")
