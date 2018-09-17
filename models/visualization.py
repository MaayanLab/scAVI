import numpy as np
from sklearn import decomposition, manifold
from .gene_expression import log10_and_zscore

## Visualization functions:
def do_pca(X, n_components=3):
	X = log10_and_zscore(X)
	pca = decomposition.PCA(n_components=n_components)
	return pca.fit_transform(X)


def do_tsne(X, n_components=3):
	X = log10_and_zscore(X)
	pca = decomposition.PCA(n_components=min(50, X.shape[1]))
	X_pca = pca.fit_transform(X)
	if n_components == 3:
		n_iter = 2000
	else:
		n_iter = 1000

	tsne = manifold.TSNE(n_components=n_components, 
		n_iter=n_iter,
		random_state=2018)
	return tsne.fit_transform(X_pca)


class Visualization(object):
	"""docstring for Visualization"""
	coll = 'vis'
	def __init__(self, ged=None, name=None, func=None, **kwargs):
		self.ged = ged # GeneExpressionDataset instance
		self.name = name
		self.func = lambda x: func(x, **kwargs)

	def compute_visualization(self):
		# make sure it is z-scored
		# if not self.ged.is_zscored():
		# 	self.ged.log10_and_zscore()
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
		if self.coords.shape[1] == 3:
			doc['z'] = self.coords[:, 2].tolist()

		insert_result = db[self.coll].insert_one(doc)
		return insert_result.inserted_id
	
	@classmethod
	def load(cls, dataset_id, name, db, n_dim=2):
		'''Load from DB'''
		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'name': name}
			]})
		obj = cls(name=doc['name'])
		if n_dim == 2:
			obj.coords = np.array([doc['x'], doc['y']]).T
		else:
			obj.coords = np.array([doc['x'], doc['y'], doc['z']]).T
		return obj


