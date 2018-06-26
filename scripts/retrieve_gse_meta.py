import sys
sys.path.append('../')
import geo_query
from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['geo']

coll.create_index('Series_geo_accession', unique=True)

geo_ids_with_meta = set(coll.distinct('Series_geo_accession'))
dataset_ids = db['dataset'].distinct('id')
# remove super series
dataset_ids = [x.split('\t')[0] for x in dataset_ids]

for dataset_id in dataset_ids:
	if dataset_id.startswith('GSE'):
		if dataset_id not in geo_ids_with_meta:
			meta = geo_query.download_and_parse_meta(dataset_id)

			coll.insert_one(meta)


# update dataset_id for subseries of super series
dataset_ids = db['dataset'].distinct('id')
for dataset_id in dataset_ids:
	if len(dataset_id.split('\t')) == 2:
		print dataset_id
		sub_series_id = dataset_id.split('\t')[0]

		db['dataset'].update_one({'id': dataset_id}, 
			{'$set': {'id': sub_series_id}})

		db['expression'].update_many({'dataset_id': dataset_id},
			{'$set': {'dataset_id': sub_series_id}})


		db['enrichr'].update_many({'dataset_id': dataset_id},
			{'$set': {'dataset_id': sub_series_id}})

		db['vis'].update_many({'dataset_id': dataset_id},
			{'$set': {'dataset_id': sub_series_id}})

