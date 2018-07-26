import os
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# from gene_expression import *
# from enrichment import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def nan_to_none(x):
	'''Convert np.nan to None.'''
	try:
		if np.isnan(x):
			x = None
	except TypeError:
		pass
	return x

def load_graphs_meta():
	'''Load and preprocess the meta for graphs in the `data/graphs` dir.
	'''
	graphs = []
	graphs_dir = os.path.join(SCRIPT_DIR, 'data/graphs')
	for graph_file in os.listdir(graphs_dir):
		graph_meta = {
			'name': graph_file,
			'display_name': graph_file.strip('.json'),
		}
		graphs.append(graph_meta)
	return graphs

def load_predicted_cell_types():
	preds_df = pd.read_csv(os.path.join(SCRIPT_DIR, 'data/predicted_cell_types.csv'))
	return preds_df.set_index(preds_df.columns[0])

def load_cell_meta_from_file():
	meta_file = os.path.join(SCRIPT_DIR, 'data/Index Sort Matrix_04_MR.xlsx')
	meta_df = pd.read_excel(meta_file, sheetname='Sheet1')
	meta_df = meta_df.set_index('Well')
	meta_df = meta_df[meta_df.columns[2:]]
	
	meta_df = meta_df.transpose()
	meta_df.index.name = 'sample_ids'
	meta_df['Plate'] = meta_df.index.map(lambda x:x.split('_')[0])
	meta_df['FSC'] = meta_df['FSC'].fillna(0)
	meta_df['SSC'] = meta_df['SSC'].fillna(0)

	meta_df.fillna('unknown', inplace=True)
	preds_df = load_predicted_cell_types()
	meta_df = meta_df.merge(preds_df, left_index=True, right_index=True, how='left')
	print meta_df.shape
	return meta_df


def minmax_scaling(arr):
	scl = MinMaxScaler((0, 20))
	arr = scl.fit_transform(arr.reshape(-1, 1))
	return arr[:, 0]

from sklearn import cluster
def clustering(x, y, clstr):
	data = np.zeros((len(x), 2))
	data[:, 0] = x
	data[:, 1] = y
	clstr.fit(data)
	return clstr.labels_


def load_vis_df(vis, gds):
	graph_df = pd.DataFrame({
		'sample_ids': gds.sample_ids,
		'x': vis.coords[:, 0].tolist(),
		'y': vis.coords[:, 1].tolist(),
		}).set_index('sample_ids')
	graph_df.index.name = 'sample_id'
	# Scale the x, y 
	graph_df['x'] = minmax_scaling(graph_df['x'].values)
	graph_df['y'] = minmax_scaling(graph_df['y'].values)
	# Perform clustering
	graph_df['DBSCAN-clustering'] = clustering(graph_df['x'].values, graph_df['y'].values,
		clstr = cluster.DBSCAN(min_samples=5, 
			eps=0.7))
	graph_df['KMeans-clustering'] = clustering(graph_df['x'].values, graph_df['y'].values, 
		cluster.KMeans(n_clusters=10))
	# Merge with meta_df
	graph_df = graph_df.merge(gds.meta_df, how='left', left_index=True, right_index=True)
	return graph_df

def load_psudotime_df(pe, gds):
	graph_df = pd.DataFrame({
		'sample_ids': gds.sample_ids,
		'x': pe.coords[:, 0].tolist(),
		'y': pe.coords[:, 1].tolist(),
		}).set_index('sample_ids')
	graph_df.index.name = 'sample_id'
	# Scale the x, y 
	graph_df['x'] = minmax_scaling(graph_df['x'].values)
	graph_df['y'] = minmax_scaling(graph_df['y'].values)
	# Merge with meta_df
	graph_df = graph_df.merge(gds.meta_df, how='left', left_index=True, right_index=True)
	# Merge with estimated attributes from pe
	data_df = pe.results['data_df']
	data_df.index = graph_df.index
	graph_df = graph_df.merge(data_df, left_index=True, right_index=True)
	return graph_df

