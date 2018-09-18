import sys
sys.path.append('../')
from models.database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from models.gene_expression import *

dataset_ids = ['7f35ecfbcad6ba783535843627f53f3e', 'c09ea8237bef65e82f5a6025262089b7',
	'c5e603148c1b5639f1545ce7f60b59de']
for dataset_id in dataset_ids:
	GeneExpressionDataset.remove_all(dataset_id, db)
