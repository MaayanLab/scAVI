'''
Handle cell type predictions.
'''
import os
import cPickle as pickle
import numpy as np
import pandas as pd

from gene_expression import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def load_objects_from_files(*args):
	ret = []
	for fn in args:
		fp = os.path.join(SCRIPT_DIR, 'data/models', fn)
		if fn.endswith('.npz'):
			obj = np.load(fp)
		else:
			obj = pickle.load(open(fp, 'rb'))
		ret.append(obj)
	return ret

def get_top1_labels(Y_probas):
	'''Get most probable predicted labels for samples.
	'''
	mask = np.argmax(Y_probas.values, axis=1)
	return Y_probas.columns[mask].tolist()


class Prediction(object):
	"""docstring for Prediction"""
	coll = 'preds'
	def __init__(self, ged=None, name=None, 
		preprocessor=None, model=None,
		npz=None
		):
		self.ged = ged # GeneExpressionDataset instance
		self.name = name
		self.preprocessor = preprocessor
		self.model = model
		self.labels = npz['labels'] # labels of the prediction model
		self.genes = npz['genes'] # genes of the preprocessor

	def predict_proba(self):
		# check if data is read counts
		if self.ged.df.dtypes[0] != np.float:
			mat = compute_CPMs(self.ged.df)

		else:
			mat = self.ged.df

		assert not self.ged.is_zscored()

		mat = mat.loc[self.genes].fillna(0)
		mat = mat.values.T # sample by genes
		mat = self.preprocessor.transform(mat)

		# samples by predicted attrs
		Y_probas = np.array([y[:, 1] for y in self.model.predict_proba(mat)]).T 
		Y_probas = pd.DataFrame(Y_probas, 
			index=self.ged.sample_ids,
			columns=self.labels)
		self.Y_probas = Y_probas
		self.top1_labels = get_top1_labels(Y_probas)
		return Y_probas

	def save(self, db):
		pass

	@classmethod
	def load(cls, dataset_id, name, db):
		'''Load from DB'''

		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'name': name}
			]})
		obj = cls(ged=None, name=name)
		obj.Y_probas = pd.DataFrame(doc['scores'], index=doc['sample_ids'])
		obj.top1_labels = doc['top1_labels']
		return obj

	@classmethod
	def get_label_probas(cls, dataset_id, name, label, db):
		'''Given dataset_id, name, term, find the scores of the samples.
		'''
		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'name': name}
			]}, 
			{'scores.%s'%term:True, '_id': False}
			)
		doc['scores'][term] = map(nan_to_none, doc['scores'][term])
		return doc['scores']

	@classmethod
	def get_top_labels(cls, dataset_id, name, db):
		'''Return the list top predicted labels for samples.
		'''
		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'name': name}
			]}, 
			{'top1_labels':True, '_id':False}
			)
		return {name: map(nan_to_none, doc['top1_labels'])}


