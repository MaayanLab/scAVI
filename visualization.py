import numpy as np
from sklearn import decomposition, manifold

class Visualization(object):
	"""docstring for Visualization"""
	coll = 'vis'
	def __init__(self, ged=None, name=None, func=None):
		self.ged = ged # GeneExpressionDataset instance
		self.name = name
		self.func = func

	def compute_visualization(self):
		coords = self.func(self.ged.df.values.T)
		self.coords = coords
		return self.coords
		
	def save(self, db):
		'''Save to DB'''
		doc = {
			'name': self.name,
			'dataset_id': self.ged.id,
			'x': list(self.coords[:, 0]),
			'y': list(self.coords[:, 1])
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
		return obj


