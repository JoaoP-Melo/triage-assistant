import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pymongo import MongoClient

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_USERNAME = os.getenv("MONGODB_USERNAME")

Base = declarative_base()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


client = MongoClient(MONGODB_URL)
database = client[MONGODB_USERNAME]

def get_mongo_db():
    return database