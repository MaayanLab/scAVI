'''
Run 3d PCA and tSNE for all datasets in DB
'''
import sys
sys.path.append('../')
from joblib import Parallel, delayed
from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from classes import *

# Get a list of existing GSEs in the DB
existing_dataset_ids = db['dataset'].find({
	'sample_ids.30': {'$exists': True}
	}).distinct('id')

dataset_ids_with_3d = db['vis'].find({'name': 'tSNE-3d'}).distinct('dataset_id')

dataset_ids_to_work = set(existing_dataset_ids) - set(dataset_ids_with_3d)
print '# datasets to run 3d: %d' % len(dataset_ids_to_work)

for dataset_id in dataset_ids_to_work:
	if dataset_id.startswith('GSE'):
		gds = GEODataset.load(dataset_id, db)
	else:
		gds = GeneExpressionDataset.load(dataset_id, db)

	print 'Dataset %s loaded, shape: (%d, %d)' % (dataset_id, gds.df.shape[0], gds.df.shape[1])

	print 'Computing 3d PCA'
	vis = Visualization(ged=gds, name='PCA', func=do_pca)
	coords = vis.compute_visualization()
	print coords.shape

	# remove pca vis in the db
	db['vis'].delete_one({'name': 'PCA', 'dataset_id': dataset_id})
	# save the 3d PCA coords
	vis.save(db)

	print 'Computing 3d tSNE'
	vis = Visualization(ged=gds, name='tSNE-3d', func=do_tsne)
	coords = vis.compute_visualization()
	print coords.shape
	vis.save(db)

