from database.database import local_session
from database.models import Admin
from sqlalchemy import select
from services.auth import pass_hasher
import asyncio
async def create_admin():
    username=input("Enter username here: ")
    password=input("Enter password here: ")
    email=input("Enter email here: ")
    async with local_session() as db:
        check= await db.scalar(select(Admin))
        if check:
            print("Admin already exists.")
            return
        admin=Admin(username=username, password=pass_hasher.hash(password), email=email)
        db.add(admin)
        await db.commit()
        print("Admin created. ")
if __name__ == "__main__":
    asyncio.run(create_admin)