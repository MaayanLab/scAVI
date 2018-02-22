import os, sys
import json
import time
import StringIO
import numpy as np
np.random.seed(10)
import pandas as pd

from flask import Flask, request, redirect, render_template, \
	jsonify, send_from_directory, abort, Response, send_file

from utils import *

from database import *
from classes import *

ENTER_POINT = os.environ['ENTER_POINT']

app = Flask(__name__, static_url_path=ENTER_POINT, static_folder=os.getcwd())
app.debug = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 6
app.config['MONGO_URI'] = MONGOURI

mongo.init_app(app)

# @app.before_first_request
# def load_globals():
# 	global meta_df, graph_df
# 	global graphs # meta data of the graphs for the header
# 	global d_all_graphs # preload all graphs
# 	global graph_name_full
# 	global CPM_df 
# 	global genes_avg_expression

# 	global d_lib_combined_score_df
# 	global d_lib_top_terms
# 	global all_terms_df


# 	graph_name_full = 'FWD_kNN_3.json'
# 	graphs = load_graphs_meta()
# 	# Load cell meta
# 	meta_df = load_cell_meta_from_file()

# 	graph_df = load_graph_from_db(graph_name_full, meta_df)

# 	# Load all the graphs
# 	d_all_graphs = {}
# 	for graph_rec in graphs:
# 		graph_name = graph_rec['name']
# 		graph_df_ = load_graph_from_db(graph_name, meta_df)
# 		d_all_graphs[graph_name] = graph_df_

# 	# Load expression matrix
# 	CPM_df = load_CPM_matrix()
# 	genes_avg_expression = CPM_df.mean(axis=1).to_frame()
# 	genes_avg_expression.columns = ['avg_expression']
# 	genes_avg_expression.index.name = 'gene'
# 	genes_avg_expression = genes_avg_expression.reset_index()

# 	# Load enrichment results
# 	d_lib_combined_score_df, d_lib_top_terms, all_terms_df = load_all_enrichment_results()
# 	return


@app.route(ENTER_POINT + '/')
def index_page():
	# The default main page
	sdvConfig = {
		'colorKey': 'Sample_source_name_ch1',
		'shapeKey': 'Sample_source_name_ch1',
		'labelKey': ['Sample_geo_accession', 'Sample_source_name_ch1'],
	}

	return render_template('index.html', 
		script='main',
		ENTER_POINT=ENTER_POINT,
		graphs=graphs,
		graph_name=graph_name_full,
		sdvConfig=json.dumps(sdvConfig),
		)

@app.route(ENTER_POINT + '/graph_page/<string:graph_name>/<string:dataset_id>')
def graph_page(graph_name, dataset_id):
	# defaults
	sdvConfig = {
		'colorKey': 'Sample_source_name_ch1',
		'shapeKey': 'Sample_source_name_ch1',
		'labelKey': ['Sample_geo_accession', 'Sample_source_name_ch1'],
	}


	return render_template('index.html', 
		script='main',
		ENTER_POINT=ENTER_POINT,
		result_id='hello',
		# graphs=graphs,
		graph_name=graph_name,
		dataset_id=dataset_id,
		sdvConfig=json.dumps(sdvConfig),
		)


@app.route('/<path:filename>')
def serve_static_file(filename):
	'''Serve static files.
	'''
	return send_from_directory(app.static_folder, filename)


@app.route(ENTER_POINT + '/graph/<string:graph_name>/<string:dataset_id>', methods=['GET'])
def load_graph_layout_coords(graph_name, dataset_id):
	'''API for different graphs'''
	if request.method == 'GET':
		gds = GEODataset.load(dataset_id, mongo.db)
		vis = Visualization.load(dataset_id, graph_name, mongo.db)

		graph_df = load_vis_df(vis, gds)
		return graph_df.reset_index().to_json(orient='records')
		# if graph_name == 'full':
		# 	print graph_df.shape
		# 	return graph_df.reset_index().to_json(orient='records')
		# else:
		# 	# graph_df_, meta_df_ = load_graph_from_db(graph_name, drug_meta_df)
		# 	# print graph_df_.head()
		# 	graph_df_ = d_all_graphs[graph_name]
		# 	return graph_df_.reset_index().to_json(orient='records')


'''
Gene expression search endpoints
'''
@app.route(ENTER_POINT + '/gene/query/<string:dataset_id>/<string:query_string>', methods=['GET'])
def search_genes(query_string, dataset_id):
	'''Endpoint handling gene search.
	'''
	if request.method == 'GET':
		mask = genes_avg_expression['gene'].str.contains(query_string, case=False)
		return genes_avg_expression.loc[mask].to_json(orient='records') 

@app.route(ENTER_POINT + '/gene/get/<string:gene>', methods=['GET'])
def retrieve_gene_expression(gene):
	'''Get the expression values of a gene across samples.
	'''
	cpm_arr = CPM_df.loc[gene].values
	cpm_arr = np.log10(cpm_arr + 1.)
	cpm_arr = (cpm_arr - cpm_arr.mean()) / cpm_arr.std()
	return jsonify({gene: cpm_arr.tolist()})


'''
Enriched terms search endpoints
'''
@app.route(ENTER_POINT + '/term/query/<string:query_string>', methods=['GET'])
def search_terms(query_string):
	if request.method == 'GET':
		mask = all_terms_df['term'].str.contains(query_string, case=False)
		return all_terms_df.loc[mask].to_json(orient='records') 

@app.route(ENTER_POINT + '/term/get/<string:term>', methods=['GET'])
def retrieve_term_enrichment(term):
	gene_set_library = all_terms_df.loc[all_terms_df['term'] == term].iloc[0]['library']
	combined_scores = d_lib_combined_score_df[gene_set_library].loc[term]
	combined_scores = combined_scores.fillna(np.nanmin(combined_scores))
	return jsonify({term: combined_scores.tolist()})
	# return jsonify({term: map(nan_to_none, combined_scores)})

'''
Most enriched terms within a gene set library
'''
@app.route(ENTER_POINT + '/library/query', methods=['GET'])
def get_libraries():
	if request.method == 'GET':
		# return jsonify([{'library': d_lib_top_terms.keys()}])
		return jsonify([{'name': lib} for lib in d_lib_top_terms.keys()])

@app.route(ENTER_POINT + '/library/get/<string:library>', methods=['GET'])
def retrieve_library_top_terms(library):
	top_terms = map(nan_to_none, d_lib_top_terms[library])
	return jsonify({library: top_terms})

from jinja2 import Markup
app.jinja_env.globals['include_raw'] = lambda filename : Markup(app.jinja_loader.get_source(app.jinja_env, filename)[0])


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, threaded=True)


