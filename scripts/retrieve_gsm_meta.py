# import warnings
import sys
sys.path.append('../')
# with warnings.catch_warnings():
# 	warnings.simplefilter("ignore")
# 	import geo_query as gq
from database import *
from geo_meta import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']

coll_gse = db['geo']
coll = db['gsm']

index_field = 'geo_accession'

coll_gse.create_index(index_field, unique=True)
coll.create_index(index_field, unique=True)

gsms_with_meta = set(coll.distinct(index_field))
dataset_ids = db['dataset'].distinct('id')
# remove super series
dataset_ids = [x.split('\t')[0] for x in dataset_ids]

print len(dataset_ids)

c = 0
for dataset_id in dataset_ids:
	if dataset_id.startswith('GSE'):

		gse = GSE(dataset_id)
		gse.retrieve()
		gse.save(db)

	c += 1
	if c % 20 == 0:
		print c, len(dataset_ids)
