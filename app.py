import os, sys
import json
import time
import StringIO
from collections import Counter
import subprocess
import numpy as np
np.random.seed(10)
import pandas as pd

from flask import Flask, request, redirect, render_template, \
	jsonify, send_from_directory, abort, Response, send_file
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit

import encrypt
from utils import *

from database import *
from classes import *

ENTER_POINT = os.environ['ENTER_POINT']

app = Flask(__name__, static_url_path=ENTER_POINT, static_folder=os.path.join(os.getcwd(), 'static'))
app.debug = bool(int(os.environ.get('debug', True)))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 6
app.config['MONGO_URI'] = os.environ.get('MONGOURI', MONGOURI)
app.config['UPLOAD_FOLDER'] = os.path.join(SCRIPT_DIR, 'data/uploads')

mongo.init_app(app)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route(ENTER_POINT + '/')
def index_page():
	# The default main page
	return redirect(ENTER_POINT+'/all', code=302)


@app.route(ENTER_POINT + '/all')
def all_datasets():
	dataset_ids = mongo.db['dataset'].distinct('id')

	geo_datasets = []
	for dataset_id in dataset_ids:
		if dataset_id.startswith('GSE'):
			gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
			geo_datasets.append(gds)

	return render_template('datasets.html', 
			ENTER_POINT=ENTER_POINT,
			geo_datasets=geo_datasets
			)


from upload_utils import *
from threading import Lock
all_threads = {}
all_loggers = {}
from background_pipeline import *


@app.route(ENTER_POINT + '/upload', methods=['GET', 'POST'])
def upload_files():
	if request.method == 'POST':
		data_file = request.files['data']
		metadata_file = request.files['metadata']

		if data_file and allowed_file(data_file.filename) and \
			metadata_file and allowed_file(metadata_file.filename):
			data_filename = secure_filename(data_file.filename)
			# data_file.save(os.path.join(app.config['UPLOAD_FOLDER'], data_filename))
			metadata_filename = secure_filename(metadata_file.filename)
			# metadata_file.save(os.path.join(app.config['UPLOAD_FOLDER'], metadata_filename))

			# parse uploaded files
			expr_df, meta_df = parse_uploaded_files(data_file, metadata_file)
			try:
				expr_dtype = expression_is_valid(expr_df)
			except ValueError as e:
				print expr_df.head()
				abort(str(e))
			else:
				if expr_dtype == 'counts':
					expr_df = compute_CPMs(expr_df)

				# parse into GeneExpressionDataset object
				dataset = GeneExpressionDataset(expr_df, meta={'meta_df': meta_df.to_dict('list')})
				# check if dataset exists
				dataset_exists = True
				if not dataset.exists(mongo.db):
					dataset_exists = False
					dataset.save(mongo.db)
					# run the pipeline in background
					# p = subprocess.Popen(['python', 'pipeline.py', '-i', dataset.id], 
					# 	stdout=subprocess.PIPE)
					dataset_id = dataset.id

					# thread_lock = Lock()
					# with thread_lock:
					if dataset_id not in all_threads:
						# create logger for the job
						logger = Logger(dataset_id)
						all_loggers[dataset_id] = logger
						thread = socketio.start_background_task(target=background_pipeline, 
							socketio=socketio,
							dataset_id=dataset_id,
							gene_set_libraries='KEGG_2016,ARCHS4_Cell-lines',
							logger=logger
							)
						all_threads[dataset_id] = thread


			return render_template('upload_success.html',
					ENTER_POINT=ENTER_POINT,
					data_filename=data_filename,
					metadata_filename=metadata_filename,
					dataset_exists=dataset_exists,
					ds=dataset)

	return render_template('upload.html',
			ENTER_POINT=ENTER_POINT)


@app.route(ENTER_POINT + '/progress/<string:dataset_id>', methods=['GET'])
def check_progress(dataset_id):
	'''Given dataset_id, return some metadata and the progress of its associated 
	objects: visualizations, enrichment.'''
	ds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
	if ds is None:
		abort(404)
	else:
		visualizations = mongo.db['vis'].find({'dataset_id': dataset_id}, 
			{'_id': False, 'name':True})
		enrichments = mongo.db['enrichr'].find({'dataset_id': dataset_id}, 
			{'_id': False, 'gene_set_library':True})
		er_pendings = mongo.db['enrichr_temp'].find({'dataset_id': dataset_id}, 
			{'_id': False, 'gene_set_library':True})

		ds.visualizations = [vis for vis in visualizations]
		ds.enrichment_results = [er for er in enrichments]
		er_pendings = Counter([er['gene_set_library'] for er in er_pendings])
		ds.er_pendings = [{'gene_set_library': key, 'count': val} for key, val in er_pendings.items()]	
		
		# run the pipeline
		return render_template('progress.html', 
			ENTER_POINT=ENTER_POINT,
			logger=all_loggers[dataset_id],
			ds=ds)



@app.route(ENTER_POINT + '/graph_page/<string:dataset_id>/<string:graph_name>')
def graph_page(graph_name, dataset_id):
	# defaults
	sdvConfig = {
		'labelKey': ['sample_id', 'Sample_source_name_ch1'],
	}
	# pick the attributes for default shaping and coloring
	if dataset_id.startswith('GSE'):
		gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
	else:
		gds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
	n_samples = len(gds.sample_ids)
	d_col_nuniques = {}
	for col in gds.meta_df.columns:
		d_col_nuniques[col] = gds.meta_df[col].nunique()

	d_col_nuniques = sorted(d_col_nuniques.items(), key=lambda x:x[1])
	sdvConfig['colorKey'] = d_col_nuniques[1][0]
	sdvConfig['shapeKey'] = d_col_nuniques[0][0]
			
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
		if dataset_id.startswith('GSE'):
			gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
		else:
			gds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
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


'''
Pages for samples
'''
@app.route(ENTER_POINT + '/sample/<string:sample_id>', methods=['GET'])
def sample_landing_page(sample_id):
	# find the dataset id using the sample_id
	dataset_id = mongo.db['dataset'].find_one({'sample_ids': sample_id}, {'id':True, '_id':False})['id']

	if dataset_id.startswith('GSE'):
		gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
	else:
		gds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
	# prepare meta
	sample_meta = gds.meta_df.loc[sample_id]#.to_dict()
	sample_meta['sample_id'] = sample_id

	# get the idx of the sample in the dataset
	idx = gds.sample_ids.tolist().index(sample_id)

	# prepare gene expression
	cur = mongo.db['expression'].find(
		{'dataset_id': dataset_id},
		{'gene':True, 'values': {'$slice':[idx, 1]}, '_id': False}
	)

	recs = [{'gene':doc['gene'], 'val': doc['values'][0]} for doc in cur]
	sorted_zscores = pd.DataFrame.from_records(recs).sort_values('val')

	top_up_genes = sorted_zscores[-20:][::-1].to_dict(orient='records')
	top_dn_genes = sorted_zscores[:20][::-1].to_dict(orient='records')

	# prepare enrichment
	enrichment = {}
	cur = mongo.db['enrichr'].find({'dataset_id': dataset_id}, 
		{'gene_set_library':True, 'scores': True, '_id':False})
	for doc in cur:
		lib = doc['gene_set_library']
		recs = [{'term': term, 'score': scores[idx]} for term, scores in doc['scores'].iteritems()]
		sorted_scores = pd.DataFrame.from_records(recs).sort_values('score', na_position='first')
		top_terms = sorted_scores[-10:][::-1].to_dict(orient='records')
		enrichment[lib] = top_terms

	sample_data = {
		'genes': 	top_up_genes + top_dn_genes,
		'enrichment': enrichment
	}
	return render_template('sample_page.html', 
		sample_meta=sample_meta,
		sample_data=json.dumps(sample_data),
		ENTER_POINT=ENTER_POINT,
		)

'''
Endpoints for brush selection
'''
@app.route(ENTER_POINT + '/brush/<string:dataset_id>', methods=['POST'])
def encrypt_sample_ids(dataset_id):
	if request.method == 'POST':
		req_data = json.loads(request.data)
		# print req_data
		sample_ids = req_data['ids']
		sample_ids_str = ','.join(sorted(sample_ids))
		sample_ids_hash = encrypt.encrypt(sample_ids_str)
		return jsonify({'hash': sample_ids_hash})

@app.route(ENTER_POINT + '/brush/<string:dataset_id>/<string:sample_ids_hash>', methods=['GET'])
def decrypt_sample_ids(dataset_id, sample_ids_hash):
	'''Decrypt sample_ids from the hash then render template for the brush modal.
	'''
	sample_ids = encrypt.decrypt(sample_ids_hash).split(',')

	if dataset_id.startswith('GSE'):
		gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
	else:
		gds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
	# prepare meta
	samples_meta = gds.meta_df.loc[sample_ids]
	# filter out columns with equal number of unique values
	samples_meta = samples_meta.loc[:, samples_meta.nunique() < len(sample_ids)]

	# get the mask of the selected samples in the dataset
	mask = np.in1d(gds.sample_ids, sample_ids)

	# prepare gene expression
	cur = mongo.db['expression'].find(
		{'dataset_id': dataset_id},
		{'gene':True, 'values': True, '_id': False}
	)
	# pick to top expressed genes
	zscores_df = pd.DataFrame.from_dict({doc['gene'] : np.array(doc['values'])[mask] for doc in cur})
	sorted_zscores = zscores_df.median().sort_values()
	top_up_genes = sorted_zscores[-20:][::-1].index
	top_dn_genes = sorted_zscores[:20][::-1].index
	top_genes = list(top_up_genes) + list(top_dn_genes)
	top_genes_zscores_df = zscores_df.loc[:, top_genes]

	# prepare enrichment
	enrichment = {}
	cur = mongo.db['enrichr'].find({'dataset_id': dataset_id}, 
		{'gene_set_library':True, 'scores': True, '_id':False})
	for doc in cur:
		lib = doc['gene_set_library']
		scores_df = pd.DataFrame.from_dict({term: np.array(scores)[mask] for term, scores in doc['scores'].iteritems() })\
			.fillna(0)
		sorted_scores = scores_df.median().sort_values(ascending=False, na_position='last')
		top_terms = sorted_scores[:10].index
		top_terms_scores = scores_df.loc[:, top_terms].melt().to_dict(orient='list') # {term: [values]}
		enrichment[lib] = top_terms_scores

	plot_data = { 
		'samples_meta': samples_meta.to_dict(orient='list'),
		'genes': top_genes_zscores_df.melt().to_dict(orient='list'), # {'gene': [genes], 'value': [values]}
		'enrichment' : enrichment,
	}

	return render_template('brush-modal.html',
		meta_df=samples_meta,
		plot_data=json.dumps(plot_data),
		ENTER_POINT=ENTER_POINT,
		)


'''
Error handlers.
'''
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', ENTER_POINT=ENTER_POINT), 404


from jinja2 import Markup
app.jinja_env.globals['include_raw'] = lambda filename : Markup(app.jinja_loader.get_source(app.jinja_env, filename)[0])


'''
SocketIO endpoints
'''
@socketio.on('connect', namespace='/test')
def test_connect():
	'''Send message to client when one connects.
	'''
	# global thread
	# with thread_lock:
	#     if thread is None:
	#         thread = socketio.start_background_task(target=background_pipeline_test, socketio=socketio)
	emit('my_response', {'data': 'Connected', 'count': 0})

# @socketio.on('check_status', namespace='/test')
@socketio.on('check_status')
def check_pipeline_status(msg):
	'''Send specific message to client when one wants to check the status of a dataset.
	'''
	dataset_id = msg['id']
	print dataset_id


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
	print('Client disconnected', request.sid)



if __name__ == '__main__':
	# app.run(host='0.0.0.0', port=5000, threaded=True)
	socketio.run(app, host='0.0.0.0', port=5000)


