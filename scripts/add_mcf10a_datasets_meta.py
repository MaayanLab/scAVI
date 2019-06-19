import os
import json
from pymongo import MongoClient

MONGOURI = os.environ.get('MONGOURI')
mongo = MongoClient(MONGOURI)

db = mongo['SCV0']
coll = db['dataset_meta']

dataset_meta = json.load(open('mcf10a_datasets_meta.json', 'r'))

coll.insert_many(dataset_meta)
