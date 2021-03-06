from pymongo import MongoClient, ASCENDING, TEXT

MONGOURI = 'mongodb://127.0.0.1:27017/SCV'

mongo = MongoClient(MONGOURI)

db = mongo['SCV']

coll_ds = db['dataset']
coll_expr = db['expression']
coll_enrichr = db['enrichr']
coll_vis = db['vis']
coll_geo = db['geo']


coll_ds.drop()
coll_expr.drop()
coll_enrichr.drop()
coll_vis.drop()


coll_ds.create_index('id', unique=True)

coll_expr.create_index([('dataset_id', ASCENDING), ('gene', ASCENDING)], 
	unique=True)

coll_enrichr.create_index([('dataset_id', ASCENDING), ('gene_set_library', ASCENDING)], 
	unique=True)
coll_enrichr.create_index('terms') # keywords index

coll_vis.create_index([('dataset_id', ASCENDING), ('name', ASCENDING)], 
	unique=True)

coll_geo.create_index([('title', TEXT), ('summary', TEXT)], default_language='english')
