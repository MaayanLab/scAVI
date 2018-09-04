'''Change the structures of dataset and enrichr collections to 
1. Enable multiple enrichment results on the one (dataset, gene_set_library) pair.
2. Allows multiple userListId for each cell
'''

from pymongo import MongoClient, ASCENDING

from models.database import *

mongo = MongoClient(MONGOURI)
db = mongo['SCV']

coll_enrichr = db['enrichr']


coll_enrichr.drop_indexes()

coll_enrichr.create_index([('dataset_id', ASCENDING), ('gene_set_library', ASCENDING), ('type', ASCENDING)], 
	unique=True)
coll_enrichr.create_index('terms') # keywords index

# Add `type` for all existing documents in enrichr collection
coll_enrichr.update_many({}, {'$set': {'type': 'genewise-z'}})


# Before:
# d_sample_userListId is {sample_id: userListId}
# After:
# d_sample_userListId {type: {sample_id: userListId}}
coll_ds = db['dataset']
cur = coll_ds.find({'d_sample_userListId': { '$exists': True}}, 
	{'id':True, '_id':False, 'd_sample_userListId': True})

for doc in cur:
	d_sample_userListId = doc['d_sample_userListId']
	coll_ds.update_one({'id': doc['id']}, 
		{'$set': 
			{'d_sample_userListId': {'genewise-z': d_sample_userListId}}
		})
