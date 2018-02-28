import numpy as np
from sklearn import decomposition, manifold

## Visualization functions:
def do_pca(X):
	pca = decomposition.PCA(n_components=2)
	return pca.fit_transform(X)


def do_tsne(X):
	pca = decomposition.PCA(n_components=50)
	X_pca = pca.fit_transform(X)
	tsne = manifold.TSNE(n_components=2, random_state=2018)
	return tsne.fit_transform(X_pca)


class Visualization(object):
	"""docstring for Visualization"""
	coll = 'vis'
	def __init__(self, ged=None, name=None, func=None):
		self.ged = ged # GeneExpressionDataset instance
		self.name = name
		self.func = func

	def compute_visualization(self):
		# make sure it is z-scored
		if not self.ged.is_zscored():
			self.ged.log10_and_zscore()
		coords = self.func(self.ged.df.values.T)
		self.coords = coords
		return self.coords
		
	def save(self, db):
		'''Save to DB'''
		doc = {
			'name': self.name,
			'dataset_id': self.ged.id,
			'x': self.coords[:, 0].tolist(),
			'y': self.coords[:, 1].tolist()
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


