import os
import smtplib
from email.message import EmailMessage
from datetime import datetime ,timezone
from dotenv import load_dotenv
load_dotenv()
sender=os.getenv("Email_name")
password=os.getenv("Email_pass")


def send_email(to,token):
    msg=EmailMessage()
    msg["From"]=sender
    msg["To"]=to
    msg["Subject"]="Verify Email"
    msg.set_content(f"Go to http://127.0.0.1:8000/user/verify/email and enter this code: {token}")
    msg.add_alternative(f"""
    <a href='http://127.0.0.1:8000/user/verify/email?token={token}'>Click here to verify </a>
    """,
    subtype="html")
    smtp=smtplib.SMTP_SSL("smtp.gmail.com",465)
    smtp.login(sender,password)
    smtp.send_message(msg)
    smtp.quit()

async def send_admin_email(ip):
      admin_email=os.getenv("Admin_email")
      msg=EmailMessage()
      msg["From"]=sender
      msg["To"]=admin_email
      msg.set_content(f"Someone try to Login as Admin with IP:{ip} at {datetime.now(timezone.utc)}")
      async with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
           smtp.login(send_email,password)
           smtp.send_message(msg)