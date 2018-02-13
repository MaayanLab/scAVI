import os, sys
import json
import time
import StringIO
import numpy as np
np.random.seed(10)
import requests
import pandas as pd

from flask import Flask, request, redirect, render_template, \
	jsonify, send_from_directory, abort, Response, send_file

from utils import *

ENTER_POINT = os.environ['ENTER_POINT']

app = Flask(__name__, static_url_path=ENTER_POINT, static_folder=os.getcwd())
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 6


@app.before_first_request
def load_globals():
	global meta_df, graph_df
	global graphs # meta data of the graphs for the header
	global d_all_graphs # preload all graphs
	global graph_name_full
	global CPM_df 
	global genes_avg_expression

	graph_name_full = 'FWD_kNN_3.json'
	graphs = load_graphs_meta()
	# Load cell meta
	meta_df = load_cell_meta_from_file()

	graph_df = load_graph_from_db(graph_name_full, meta_df)

	# Load all the graphs
	d_all_graphs = {}
	for graph_rec in graphs:
		graph_name = graph_rec['name']
		graph_df_ = load_graph_from_db(graph_name, meta_df)
		d_all_graphs[graph_name] = graph_df_

	# Load expression matrix
	CPM_df = load_CPM_matrix()
	genes_avg_expression = CPM_df.mean(axis=1).to_frame()
	genes_avg_expression.columns = ['avg_expression']
	genes_avg_expression.index.name = 'gene'
	genes_avg_expression = genes_avg_expression.reset_index()
	return


@app.route(ENTER_POINT + '/')
def index_page():
	# The default main page
	sdvConfig = {
		'colorKey': 'Cell Type',
		'shapeKey': 'Sorter location',
		'labelKey': ['sample_ids', 'Cell Type', 'Sort: All vs Pop', 'Sorter location'],
	}

	return render_template('index.html', 
		script='main',
		ENTER_POINT=ENTER_POINT,
		graphs=graphs,
		graph_name=graph_name_full,
		sdvConfig=json.dumps(sdvConfig),
		)

@app.route(ENTER_POINT + '/graph_page/<string:graph_name>')
def graph_page(graph_name):
	url = 'graph/%s' % graph_name
	# defaults
	sdvConfig = {
		'colorKey': 'Cell Type',
		'shapeKey': 'Sorter location',
		'labelKey': ['sample_ids', 'Cell Type', 'Sort: All vs Pop', 'Sorter location'],
	}

	if graph_name == 'graph_pert_cell_12894nodes_99.9.gml.cyjs': 
		# Signatures aggregated for pert_id x cell_id
		sdvConfig['colorKey'] = 'Cell'
		sdvConfig['shapeKey'] = 'avg_time'
		sdvConfig['labelKey'] = ['Perturbation', 'Cell', 'avg_dose', 'avg_time', 
			'Phase', 'MOA', 'n_signatures_aggregated']
	elif graph_name in ('kNN_5_layout', 'threshold_99.5'):
		# Signatures aggregated for pert_id
		sdvConfig['shapeKey'] = 'avg_pvalue'
		sdvConfig['labelKey'] = ['Perturbation', 'avg_dose', 'avg_time', 'avg_pvalue', 
					'Phase', 'MOA', 'n_signatures_aggregated']
	return render_template('index.html', 
		script='main',
		ENTER_POINT=ENTER_POINT,
		result_id='hello',
		graphs=graphs,
		graph_name=graph_name,
		sdvConfig=json.dumps(sdvConfig),
		)


@app.route('/<path:filename>')
def serve_static_file(filename):
	'''Serve static files.
	'''
	return send_from_directory(app.static_folder, filename)


@app.route(ENTER_POINT + '/graph/<string:graph_name>', methods=['GET'])
def load_graph_layout_coords(graph_name):
	'''API for different graphs'''
	if request.method == 'GET':
		if graph_name == 'full':
			print graph_df.shape
			return graph_df.reset_index().to_json(orient='records')
		else:
			# graph_df_, meta_df_ = load_graph_from_db(graph_name, drug_meta_df)
			# print graph_df_.head()
			graph_df_ = d_all_graphs[graph_name]
			return graph_df_.reset_index().to_json(orient='records')


@app.route(ENTER_POINT + '/query_genes/<string:query_string>', methods=['GET'])
def query_genes(query_string):
	'''Endpoint handling gene search.
	'''
	if request.method == 'GET':
		mask = genes_avg_expression['gene'].str.contains(query_string, case=False)
		return genes_avg_expression.loc[mask].to_json(orient='records') 

@app.route(ENTER_POINT + '/gene/<string:gene>', methods=['GET'])
def get_gene_expression(gene):
	'''Get the expression values of a gene across samples.
	'''
	cpm_arr = CPM_df.loc[gene].values
	cpm_arr = np.log10(cpm_arr + 1.)
	cpm_arr = (cpm_arr - cpm_arr.mean()) / cpm_arr.std()
	return jsonify({gene: cpm_arr.tolist()})


from jinja2 import Markup
app.jinja_env.globals['include_raw'] = lambda filename : Markup(app.jinja_loader.get_source(app.jinja_env, filename)[0])


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, threaded=True)


