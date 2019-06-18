import os
from pymongo import MongoClient, ASCENDING, TEXT

MONGOURI = os.environ['MONGOURI']

mongo = MongoClient(MONGOURI)

db = mongo['SCV0']

coll_ds = db['dataset']
coll_expr = db['expression']
coll_enrichr = db['enrichr']
coll_vis = db['vis']
coll_upload = db['upload']

coll_ds.drop()
coll_expr.drop()
coll_enrichr.drop()
coll_vis.drop()
coll_upload.drop()

coll_ds.create_index('id', unique=True)

coll_expr.create_index([('dataset_id', ASCENDING), ('gene', ASCENDING)], 
	unique=True)

coll_enrichr.create_index([('dataset_id', ASCENDING), ('gene_set_library', ASCENDING)], 
	unique=True)
coll_enrichr.create_index('terms') # keywords index

coll_vis.create_index([('dataset_id', ASCENDING), ('name', ASCENDING)], 
	unique=True)

coll_upload.create_index('dataset_id', unique=True, sparse=True)

