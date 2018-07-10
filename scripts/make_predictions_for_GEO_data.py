'''
Apply the prediction models to all available GEO data in the DB
'''
import sys
sys.path.append('../')
from joblib import Parallel, delayed
from database import *
from pymongo import MongoClient
from pymongo import MongoClient, ASCENDING

mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['preds']
coll.create_index([('dataset_id', ASCENDING), ('name', ASCENDING)], 
	unique=True)
coll.create_index('labels') # keywords index


from classes import *
from prediction import *

prediction_name = 'human_cell_type'

# Get a list of existing GSEs in the DB
existing_GSE_ids = db['dataset'].find(
	{'$and': [
		{'id': {'$regex': r'^GSE'}},
		{'organism': 'human'}
	]}
	).distinct('id')

print '# GSEs in DB: %d' % len(existing_GSE_ids)

GSE_ids_with_predictions = coll.find({'name': prediction_name}).distinct('dataset_id')

existing_GSE_ids = set(existing_GSE_ids) - set(GSE_ids_with_predictions)
print '# GSEs needs prediction', len(existing_GSE_ids)


print 'loading prediction model'
rp, model, npzf = load_objects_from_files('GaussianRandomProjection_human_N1000.pkl',
	'KNN15_correlation.pkl',
	'genes_and_cell_types_predict_human.npz')

print model.n_jobs
print npzf['labels'].shape
print npzf['genes'].shape

for gse_id in existing_GSE_ids:
	print 'Loading', gse_id
	# load data from h5 file
	ged = GEODataset(gse_id=gse_id, organism='human', 
		expression_kwargs={'CPM_cutoff':0., 'at_least_in_persent_samples':0})
	print ged.df.shape

	pred_obj = Prediction(ged=ged, name=prediction_name,
		preprocessor=rp, model=model,
		npz=npzf)

	print 'predicting cell types for ', gse_id

	Y_probas = pred_obj.predict_proba()
	print Y_probas.shape
	print pred_obj.save(db)

