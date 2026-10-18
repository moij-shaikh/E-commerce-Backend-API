
import smtplib
from email.message import EmailMessage

from config import sender , password, admin_email
import os
from datetime import datetime ,timezone
from sqlalchemy import select
from database.models import Order
import asyncio

async def send_email(ctx,to,token):
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

async def send_admin_email(ctx):
      msg=EmailMessage()
      msg["From"]=sender
      msg["To"]=admin_email
      msg.set_content(f"Someone try to Login as Admin at {datetime.now(timezone.utc)}")
      async with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
           smtp.login(send_email,password)
           smtp.send_message(msg)
           
async def send_report(ctx):
    async with ctx["local_session"]() as db:
        db_orders= await db.scalars(select(Order))
        order_list=[
            {
                "id":i.id,
                "status":i.status
            }
            for i in db_orders.all()
            ]
        total_order=len(order_list)
        completed=sum(
            1 for order in order_list
            if order["status"]=="delivered"
        )
        cancelled=sum(
            1 for order in db_orders 
            if order["status"]=="cancelled"
        )
        pending=sum(
            1 for order in db_orders
            if order["status"] == "pending"
        )
        msg=EmailMessage()
        msg["Subject"]="Daily report "
        msg["From"]=sender
        msg["To"]=admin_email
        msg.set_content(f"""
                        Total Order: {total_order}
                        Completed Order: {completed}
                        Cancelled Order: {cancelled}
                        Pending order: {pending}
                        """)
        def send_email():
             with smtplib.SMTP_SSL("smtp.gmail.com",465) as smtp:
                        smtp.login(sender,password)
                        smtp.send_message(msg)  
        await asyncio.to_thread(send_email)
        