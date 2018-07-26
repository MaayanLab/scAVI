import numpy as np
import pandas as pd

try:
	import rpy2.robjects as ro

except ImportError:
	pass

else:
	from rpy2.robjects import pandas2ri
	pandas2ri.activate()
	ro.r('''
		source('pseudotime_estimation.R')
	''')
	runMonoclePipeline = ro.globalenv['runMonoclePipeline']


def run_monocle_pipeline(df):
	'''Call the R function runMonoclePipeline then convert to results 
	to Python object.
	df: expression DataFrame indexed by genes
	'''
	rdf = pandas2ri.py2ri(df)
	res = runMonoclePipeline(rdf)
	parsed_res = {}
	for key in list(res.names):
		df = pandas2ri.ri2py(res[res.names.index(key)])
		# drop uninformative columns 
		df = df[df.columns[df.nunique() > 2]]
		parsed_res[key] = df
	return parsed_res


class PseudotimeEstimator(object):
	"""docstring for PseudotimeEstimator"""
	coll = 'vis' # share a collection with Visualization
	def __init__(self, ged=None, name=None, func=None):
		self.ged = ged # GeneExpressionDataset instance
		self.name = name
		self.func = func

	def fit(self):
		# fit the psudotime estimation model
		results = self.func(self.ged.df)
		self.results = results
		# extract x, y coords from the results
		self.coords = np.array([results['data_df']['x'], results['data_df']['y']]).T

	def save(self, db):
		'''Save to DB'''
		doc = {
			'name': self.name,
			'dataset_id': self.ged.id,
			'x': self.coords[:, 0].tolist(),
			'y': self.coords[:, 1].tolist(),
			'data_df': self.results['data_df'].drop(['x', 'y'], axis=1).to_dict(orient='list'),
			'edge_df': self.results['edge_df'].to_dict(orient='list')
		}
		insert_result = db[self.coll].insert_one(doc)
		return insert_result.inserted_id

	@classmethod
	def load(cls, dataset_id, name, db):
		'''Load from DB'''
		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'name': name}
			]})
		obj = cls(name=doc['name'])
		obj.coords = np.array([doc['x'], doc['y']]).T
		obj.results = {}
		obj.results['data_df'] = pd.DataFrame(doc['data_df'])
		obj.results['edge_df'] = pd.DataFrame(doc['edge_df'])
		return obj


## test 
# from database import *
# from pymongo import MongoClient

# MONGOURI='mongodb://146.203.54.131:27017/SCV'
# mongo = MongoClient(MONGOURI)

# db = mongo['SCV']

# from classes import *

# gse_id = 'GSE110499'
# print 'loading dataset %s' % gse_id
# gds = GEODataset.load(gse_id, db)
# print 'dataset shape: ', gds.df.shape

# pe = PseudotimeEstimator(gds, name='monocle', func=run_monocle_pipeline)
# pe.fit()
# pe.save(db)
# pe2 = PseudotimeEstimator.load(gse_id, 'monocle', db)
