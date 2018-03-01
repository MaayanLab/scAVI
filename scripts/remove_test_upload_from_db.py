import sys
sys.path.append('../')
from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from gene_expression import *

dataset_ids = ['c09ea8237bef65e82f5a6025262089b7', 'add357efaa83dbbf2c12d880a82fe8c1']
for dataset_id in dataset_ids:
	GeneExpressionDataset.remove_all(dataset_id, db)
