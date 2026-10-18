import os 
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL=os.getenv("DATABASE_URL")
JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM=os.getenv("JWT_ALGORITHM")

sender=os.getenv("Email_name")
password=os.getenv("Email_pass")

admin_email=os.getenv("admin_email")