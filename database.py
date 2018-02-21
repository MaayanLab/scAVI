from bson.objectid import ObjectId
# from pymongo import MongoClient
from flask_pymongo import PyMongo

mongo = PyMongo()
MONGOURI = 'mongodb://127.0.0.1:27017/SCV'
# db = mongo.db

