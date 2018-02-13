import os
import json, requests
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from gene_expression import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

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
	print meta_df.shape
	return meta_df


def _minmax_scaling(arr):
	scl = MinMaxScaler((-10, 10))
	arr = scl.fit_transform(arr.reshape(-1, 1))
	return arr[:, 0]

from sklearn import cluster
def _cluster(x, y, clstr):
	data = np.zeros((len(x), 2))
	data[:, 0] = x
	data[:, 1] = y
	clstr.fit(data)
	return clstr.labels_


def load_graph_from_db(graph_name, meta_df=None):
	# Find the graph by name
	graph_doc = json.load(
		open(os.path.join(SCRIPT_DIR, 'data/graphs', graph_name), 'rb')
		)
	graph_df = pd.DataFrame({
		'sample_ids': graph_doc['sample_ids'],
		'x': graph_doc['x'],
		'y': graph_doc['y'],
		}).set_index('sample_ids')
	graph_df.index.name = 'sample_ids'
	# Scale the x, y 
	graph_df['x'] = _minmax_scaling(graph_df['x'].values)
	graph_df['y'] = _minmax_scaling(graph_df['y'].values)
	# Perform clustering
	graph_df['DBSCAN-clustering'] = _cluster(graph_df['x'].values, graph_df['y'].values,
		clstr = cluster.DBSCAN(min_samples=10, eps=0.33))
	graph_df['KMeans-clustering'] = _cluster(graph_df['x'].values, graph_df['y'].values, 
		cluster.KMeans(n_clusters=30))

	# Merge with meta_df
	graph_df = graph_df.merge(meta_df, how='left', left_index=True, right_index=True)

	return graph_df

