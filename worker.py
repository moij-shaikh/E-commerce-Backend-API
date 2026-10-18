from jobs import send_admin_email , send_email, send_report
from database.database import local_session
from arq import cron
from zoneinfo import ZoneInfo

async def startup(ctx):
    ctx["local_session"]=local_session
async def shutdown(ctx):
    print("ARQ is stopped. ")


class WorkerSettings:
    functions=[send_email, send_admin_email,send_report]
    max_jobs=10
    job_timeout=60
    max_tries=3
    on_startup=startup
    on_shutdown=shutdown
    cron_jobs=[
        cron(
            send_report,
            hour=1,
            minute=0
        )
    ]
    timezone=ZoneInfo("Asia/Kolkata")