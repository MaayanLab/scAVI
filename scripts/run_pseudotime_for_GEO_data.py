'''
Apply the pseudotime estimation algorithm to all available GEO data in the DB
'''
import sys
sys.path.append('../')
from joblib import Parallel, delayed
from database import *
from pymongo import MongoClient

mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['vis']


from classes import *

pseudo_algo_name = 'monocle'

# Get a list of existing GSEs in the DB
existing_GSE_ids = db['dataset'].find(
	{'$and': [
		{'id': {'$regex': r'^GSE'}},
		{'sample_ids.30': {'$exists': True}}
	]}).distinct('id')
print '# GSEs in DB: %d' % len(existing_GSE_ids)

GSE_ids_with_pseudo = coll.find({'name': pseudo_algo_name}).distinct('dataset_id')
existing_GSE_ids = set(existing_GSE_ids) - set(GSE_ids_with_pseudo)
print '# GSEs needs prediction', len(existing_GSE_ids)

for gse_id in existing_GSE_ids:
	print 'loading dataset %s' % gse_id
	gds = GEODataset.load(gse_id, db)
	print 'dataset shape: ', gds.df.shape
	
	print 'performing %s algorithm for %s ' % (pseudo_algo_name, gse_id)
	pe = PseudotimeEstimator(gds, name=pseudo_algo_name, func=run_monocle_pipeline)
	pe.fit()
	print pe.coords.shape
	pe.save(db)

