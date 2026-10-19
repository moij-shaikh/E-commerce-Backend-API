# E-commerce Backend API

A RESTful backend API for an e-commerce application built with Python, FastAPI, and PostgreSQL. It provides user authentication, product management, shopping cart operations, order processing, admin functionality, and background task processing.

## Features

- User registration and login
- JWT authentication
- Product management
- Shopping cart
- Checkout
- Order management
- Admin endpoints
- Redis caching
- Email verification
- Database migrations

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis
- JWT

## Installation 
#### Prerequisites
make sure you have 
- python 3.12.3 or higher
- git 
- redis
- postgresql
### Setup
##### 1. Clone the repository
git clone https://github.com/moij-shaikh/E-commerce-Backend-API.git 
cd E-commerce-Backend-API

##### 2. Create a virtual environment
- for linux/Mac: 
python3 -m venv .venv
source .venv/bin/activate
- windows (git bash)
python -m venv .venv
source venv/Scripts/activate
##### 3. Install dependencies
pip install -r requirements.txt

##### 4. Configure environment variables
Create a .env file in the project root and add the following  variables.

- JWT_SECRET_KEY=" jwt secrete key"
- JWT_ALGORITHM=" jwt algorithm " 
- Email_pass= " App password for smtp server" 
- Email_name= " Gmail address"
- admin_email= "Admin gmail address" 


##### 5. Start PostgreSQL and Redis
- Install Postgresql and make database named "ecomm" . 
- Install redis .
- ensure both are ruining and configured correctly. 

##### 6. Run database migrations
alembic upgrade head

##### 7. Start the API server
uvicorn main:app --reload

###### The API should now be available at:
- API base URL: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc