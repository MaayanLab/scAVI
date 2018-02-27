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

@app.route(ENTER_POINT + '/graph_page/<string:dataset_id>/<string:graph_name>')
def graph_page(graph_name, dataset_id):
	# defaults
	sdvConfig = {
		'colorKey': 'Sample_source_name_ch1',
		'shapeKey': 'Sample_source_name_ch1',
		'labelKey': ['Sample_geo_accession', 'Sample_source_name_ch1'],
	}
	# get available visualizations in the DB
	visualizations = mongo.db['vis'].find({'dataset_id': dataset_id}, 
		{'_id':False, 'name':True})


	return render_template('index.html', 
		script='main',
		ENTER_POINT=ENTER_POINT,
		result_id='hello',
		graphs=visualizations,
		graph_name=graph_name,
		dataset_id=dataset_id,
		sdvConfig=json.dumps(sdvConfig),
		)


@app.route('/<path:filename>')
def serve_static_file(filename):
	'''Serve static files.
	'''
	return send_from_directory(app.static_folder, filename)


@app.route(ENTER_POINT + '/graph/<string:dataset_id>/<string:graph_name>', methods=['GET'])
def load_graph_layout_coords(graph_name, dataset_id):
	'''API for different graphs'''
	if request.method == 'GET':
		gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
		vis = Visualization.load(dataset_id, graph_name, mongo.db)

		graph_df = load_vis_df(vis, gds)
		return graph_df.reset_index().to_json(orient='records')


'''
Gene expression search endpoints
'''
@app.route(ENTER_POINT + '/gene/query/<string:dataset_id>/<string:query_string>', methods=['GET'])
def search_genes(query_string, dataset_id):
	'''Endpoint handling gene search.
	'''
	if request.method == 'GET':
		genes_avg_expression = GEODataset.query_gene(dataset_id, query_string, mongo.db)
		return genes_avg_expression.to_json(orient='records')

@app.route(ENTER_POINT + '/gene/get/<string:dataset_id>/<string:gene>', methods=['GET'])
def retrieve_single_gene_expression_vector(gene, dataset_id):
	'''Get the expression values of a gene across samples.
	'''
	return jsonify(GEODataset.get_gene_expr(dataset_id, gene, mongo.db))


'''
Enriched terms search endpoints
'''
@app.route(ENTER_POINT + '/term/query/<string:dataset_id>/<string:query_string>', methods=['GET'])
def search_terms(query_string, dataset_id):
	if request.method == 'GET':
		docs = mongo.db['enrichr'].find(
			{'$and': [
				{'dataset_id': dataset_id},
				{'terms': {'$elemMatch': {'$regex': ".*%s.*" % query_string, '$options': 'i'} }}
			]}, 
			{'_id':False, 'terms': True, 'gene_set_library':True})

		array_of_terms = []
		for doc in docs:
			for term in doc['terms']:
				if query_string.lower() in term.lower():
					term = {'library': doc['gene_set_library'], 'term': term}
					array_of_terms.append(term)
		return jsonify(array_of_terms)

@app.route(ENTER_POINT + '/term/get/<string:dataset_id>/<string:term>', methods=['GET'])
def retrieve_term_enrichment(dataset_id, term):
	gene_set_library = find_library_for_term(term, mongo.db)
	doc = EnrichmentResults.get_term_scores(dataset_id, gene_set_library, term, mongo.db)
	return jsonify(doc)

'''
Most enriched terms within a gene set library
'''
@app.route(ENTER_POINT + '/library/query/<string:dataset_id>', methods=['GET'])
def get_libraries(dataset_id):
	if request.method == 'GET':
		'''Return a list of available gene_set_libraries for the dataset'''
		docs = mongo.db['enrichr'].find({'dataset_id': dataset_id}, {'gene_set_library':True, '_id':False})
		return jsonify([{'name': doc['gene_set_library']} for doc in docs])

@app.route(ENTER_POINT + '/library/get/<string:dataset_id>/<string:library>', methods=['GET'])
def retrieve_library_top_terms(dataset_id, library):
	doc = EnrichmentResults.get_top_terms(dataset_id, library, mongo.db)
	return jsonify(doc)


from jinja2 import Markup
app.jinja_env.globals['include_raw'] = lambda filename : Markup(app.jinja_loader.get_source(app.jinja_env, filename)[0])


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5000, threaded=True)


