import os
from bson.objectid import ObjectId
from pymongo.cursor import CursorType
from flask_pymongo import PyMongo

mongo = PyMongo()
MONGOURI = os.environ.get('MONGOURI', 'mongodb://127.0.0.1:27017/SCV')
