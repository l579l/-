#coding=utf-8
import smtplib
from email.mime.text import MIMEText
from email.header import Header

From='1980655677@qq.com'

smtp_obj=smtplib.SMTP_SSL()
smtp_obj.connect(host='smtp.qq.com',port=465)
login=smtp_obj.login(user=From,password='yqtpbuxukabccheh')
print('登录状态:',login[1].decode('utf-8'))

def sendEmail(text,to_addrs=['13203708051@163.com'],subject='云服务器:39.107.121.203'):
    msg = MIMEText(text, 'plain', 'utf-8')
    msg['From'] = Header(From, 'utf-8')     # 发送者
    msg['To'] =  Header('', 'utf-8')          # 接收者
    msg['Subject'] = Header(subject, 'utf-8')
    smtp_obj.sendmail(from_addr=From,to_addrs=to_addrs,msg=msg.as_string())

if __name__=="__main__":
    print(sendEmail('**接口出现错误，请调试重新更正'))
