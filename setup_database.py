from pymongo import MongoClient, ASCENDING

MONGOURI = 'mongodb://127.0.0.1:27017/SCV'

mongo = MongoClient(MONGOURI)

db = mongo['SCV']

coll_ds = db['dataset']
coll_enrichr = db['enrichr']
coll_vis = db['vis']


coll_ds.drop()
coll_enrichr.drop()
coll_vis.drop()


coll_ds.create_index('id', unique=True)

coll_enrichr.create_index([('dataset_id', ASCENDING), ('gene_set_library', ASCENDING)], 
	unique=True)
coll_enrichr.create_index('terms') # keywords index

coll_vis.create_index([('dataset_id', ASCENDING), ('name', ASCENDING)], 
	unique=True)

