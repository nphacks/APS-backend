# mongo_conn/mongo.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

_client: MongoClient | None = None
_db = None


def init_mongo():
    global _client, _db
    if _client is None:
        _client = MongoClient(MONGO_URI)
        _db = _client[MONGO_DB_NAME]


def close_mongo():
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None


def get_db():
    if _db is None:
        raise RuntimeError("Mongo DB not initialized")
    return _db


def get_screenplays_collection():
    db = get_db()
    return db["screenplays"]

def get_beatboards_collection():
    db = get_db()
    return db["beatboards"]

def get_beatsheets_collection():
    db = get_db()
    return db["beatsheets"]

def get_shotlists_collection():
    db = get_db()
    return db["shotlists"]  

def get_storyboards_collection():
    db = get_db()
    return db["storyboards"]  