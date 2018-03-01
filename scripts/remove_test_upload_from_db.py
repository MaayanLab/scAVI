import sys
sys.path.append('../')
from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from gene_expression import *

dataset_ids = ['7f35ecfbcad6ba783535843627f53f3e', 'c09ea8237bef65e82f5a6025262089b7']
for dataset_id in dataset_ids:
	GeneExpressionDataset.remove_all(dataset_id, db)
