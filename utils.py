import os
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn import cluster

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def nan_to_none(x):
	'''Convert np.nan to None.'''
	try:
		if np.isnan(x):
			x = None
	except TypeError:
		pass
	return x


def minmax_scaling(arr, min=0, max=20):
	scl = MinMaxScaler((min, max))
	arr = scl.fit_transform(arr.reshape(-1, 1))
	return arr[:, 0]

def clustering(coords, clstr):
	clstr.fit(coords)
	return clstr.labels_


def load_vis_df(vis, gds):
	graph_df = pd.DataFrame({
		'sample_ids': gds.sample_ids,
		'x': vis.coords[:, 0].tolist(),
		'y': vis.coords[:, 1].tolist(),
		}).set_index('sample_ids')

	graph_df.index.name = 'sample_id'
	# Scale the x, y, (z) 
	if vis.coords.shape[1] == 3:
		graph_df['x'] = minmax_scaling(graph_df['x'].values, min=-10, max=10)
		graph_df['y'] = minmax_scaling(graph_df['y'].values, min=-10, max=10)
		graph_df['z'] = minmax_scaling(vis.coords[:, 2], min=-10, max=10)
		coords = graph_df[['x', 'y', 'z']].values
	else:
		graph_df['x'] = minmax_scaling(graph_df['x'].values)
		graph_df['y'] = minmax_scaling(graph_df['y'].values)
		coords = graph_df[['x', 'y']].values

	# Perform clustering
	graph_df['DBSCAN-clustering'] = clustering(coords,
		clstr = cluster.DBSCAN(min_samples=5, 
			eps=0.7))
	graph_df['KMeans-clustering'] = clustering(coords, 
		cluster.KMeans(n_clusters=10))
	# Filter out columns won't be used for visualization
	meta_df = gds.meta_df.loc[:, gds.meta_df.nunique() < gds.meta_df.shape[0]]
	# Merge with meta_df
	graph_df = graph_df.merge(meta_df, how='left', left_index=True, right_index=True)
	return graph_df

def load_psudotime_df(pe, gds):
	graph_df = pd.DataFrame({
		'sample_ids': gds.sample_ids,
		'x': pe.coords[:, 0].tolist(),
		'y': pe.coords[:, 1].tolist(),
		}).set_index('sample_ids')
	graph_df.index.name = 'sample_id'
	# Scale the x, y, (z) 
	if pe.coords.shape[1] == 3:
		graph_df['x'] = minmax_scaling(graph_df['x'].values, min=-10, max=10)
		graph_df['y'] = minmax_scaling(graph_df['y'].values, min=-10, max=10)
		graph_df['z'] = minmax_scaling(pe.coords[:, 2], min=-10, max=10)
		coords = graph_df[['x', 'y', 'z']].values
	else:
		graph_df['x'] = minmax_scaling(graph_df['x'].values)
		graph_df['y'] = minmax_scaling(graph_df['y'].values)
		coords = graph_df[['x', 'y']].values
	# Filter out columns won't be used for visualization
	meta_df = gds.meta_df.loc[:, gds.meta_df.nunique() < gds.meta_df.shape[0]]
	# Merge with meta_df
	graph_df = graph_df.merge(meta_df, how='left', left_index=True, right_index=True)
	# Merge with estimated attributes from pe
	data_df = pe.results['data_df']
	data_df.index = graph_df.index
	graph_df = graph_df.merge(data_df, left_index=True, right_index=True)
	return graph_df

def get_available_vis(db, dataset_id):
	'''Get available visualizations in the DB.
	also get a flag indicating whether 3d is available.
	''' 
	cur = db['vis'].find({'dataset_id': dataset_id}, 
		{'_id':False, 'name':True, 'z': True})
	vis_names = set()
	d_has3d = {}
	for doc in cur:
		name = doc['name'].split('-')[0]
		is3d = doc.has_key('z')
		if is3d:
			d_has3d[name] = True
		vis_names.add(name)
	
	return [{'name': name, 'has3d': d_has3d.get(name, False)} for name in vis_names]
