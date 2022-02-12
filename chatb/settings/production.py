import os  # noqa

from pymongo import MongoClient  # noqa

from chatb.settings.base import *  # noqa

DEBUG = True

ALLOWED_HOSTS.append("chatbotehcb.herokuapp.com")

mongodb_user = os.getenv("MONGO_USER")
mongodb_password = os.getenv("MONGO_PASSWORD")
mongodb_host = os.getenv("MONGO_HOST")
MONGO_CLIENT = MongoClient(
    f"mongodb+srv://{mongodb_user}:{mongodb_password}@{mongodb_host}"
)
MONGO_DB = MONGO_CLIENT.chatb
