import os
from bson.objectid import ObjectId
# from pymongo import MongoClient
from flask_pymongo import PyMongo

mongo = PyMongo()
# MONGOURI='mongodb://146.203.54.131:27017/SCV'
MONGOURI = os.environ.get('MONGOURI', 'mongodb://127.0.0.1:27017/SCV')
# db = mongo.db

