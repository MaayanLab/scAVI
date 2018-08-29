import os, sys
import json
import time
import StringIO
from collections import Counter, defaultdict
import subprocess
import numpy as np
np.random.seed(10)
import pandas as pd

from flask import Flask, request, redirect, render_template, \
	jsonify, send_from_directory, abort, Response, send_file
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO

import encrypt
from utils import *

from models import *

ENTER_POINT = os.environ['ENTER_POINT']
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__, static_url_path=ENTER_POINT, static_folder=os.path.join(os.getcwd(), 'static'))
app.debug = bool(int(os.environ.get('debug', True)))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 6
app.config['MONGO_URI'] = os.environ.get('MONGOURI', MONGOURI)
app.config['UPLOAD_FOLDER'] = os.path.join(SCRIPT_DIR, 'data/uploads')

mongo.init_app(app)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, path=ENTER_POINT + '/socket.io')


@app.route(ENTER_POINT + '/')
def index_page():
	# The default main page
	return redirect(ENTER_POINT+'/all', code=302)


@app.route(ENTER_POINT + '/all')
def all_datasets():
	n_cells = 0
	dataset_ids = mongo.db['dataset'].find(
		{'$and': [
			{'id': {'$regex': r'^GSE'}},
			{'sample_ids.30': {'$exists': True}}
		]}).distinct('id')
	projection = {'_id':False, 
		'pubmed_id':True, 
		'title':True, 
		'submission_date':True,
		'platform_taxid':True,
		'geo_accession':True,
		'sample_id':True
		}

	cur = mongo.db['geo'].find({'geo_accession': {'$in': dataset_ids}}, 
		projection,
		cursor_type=CursorType.EXHAUST
		)

	n_studies = cur.count()
	geo_datasets = [None] * n_studies

	i = 0
	for doc in cur:
		n_cells += len(doc['sample_id'])
		doc['n_cells'] = len(doc['sample_id'])
		organism = 'human'
		if str(doc['platform_taxid']) == '10090':
			organism = 'mouse'
		doc['organism'] = organism
		doc.pop('sample_id', None)
		geo_datasets[i] = doc
		i += 1

	stats = {'n_studies': n_studies, 'n_cells': n_cells}
	return render_template('datasets.html', 
			ENTER_POINT=ENTER_POINT,
			geo_datasets=geo_datasets,
			stats=stats
			)


from upload_utils import *
with app.app_context():
	# Set class variables
	Upload.upload_folder = app.config['UPLOAD_FOLDER']
	Upload.db = mongo.db

# from threading import Lock
from background_pipeline import *


@app.route(ENTER_POINT + '/upload', methods=['GET', 'POST'])
def upload_files():
	if request.method == 'POST':
		data_file = request.files['data']
		metadata_file = request.files['metadata']

		if data_file and allowed_file(data_file.filename) and \
			metadata_file and allowed_file(metadata_file.filename):
			data_filename = secure_filename(data_file.filename)
			data_file.save(os.path.join(app.config['UPLOAD_FOLDER'], data_filename))
			metadata_filename = secure_filename(metadata_file.filename)
			metadata_file.save(os.path.join(app.config['UPLOAD_FOLDER'], metadata_filename))

			upload_obj = Upload(data_filename, metadata_filename)
			return redirect(ENTER_POINT + '/preprocess/%s' % upload_obj.id)

	return render_template('upload.html',
			ENTER_POINT=ENTER_POINT)

@app.route(ENTER_POINT + '/preprocess/<string:upload_id>', methods=['GET'])
def preprocess_uploaded_file(upload_id):
	# Check if the upload_id exists in db
	if Upload.exists(upload_id):
		upload_obj = Upload.load(upload_id)
		# Check if upload_id has started the process
		if not upload_obj.started:
			logger = Logger(upload_id)
			thread = socketio.start_background_task(
				target=background_preprocess_pipeline, 
				# target=background_preprocess_test_pipeline,
				socketio=socketio,
				enter_point=ENTER_POINT,
				upload_id=upload_id,
				logger=logger
				)
			upload_obj.start()

		return render_template('preprocess.html',
			ENTER_POINT=ENTER_POINT,
			upload_obj=upload_obj,
			logger_msg=Logger.get_all_msg(upload_id)
			)
	else:
		abort(404)

@app.route(ENTER_POINT + '/progress/<string:dataset_id>', methods=['GET'])
def check_progress(dataset_id):
	'''Given dataset_id, return some metadata and the progress of its associated 
	objects: visualizations, enrichment.'''
	ds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
	if ds is None:
		abort(404)
	else:
		# Check if dataset_id has started the process
		if not ds.started:
			# run the pipeline
			logger = Logger(dataset_id)
			thread = socketio.start_background_task(
				target=background_pipeline, 
				socketio=socketio,
				enter_point=ENTER_POINT,
				dataset_id=dataset_id,
				gene_set_libraries='KEGG_2016,ARCHS4_Cell-lines',
				logger=logger,
				db=mongo.db
				)
			ds.start(mongo.db)

		visualizations = get_available_vis(mongo.db, dataset_id)
		enrichments = mongo.db['enrichr'].find({'dataset_id': dataset_id}, 
			{'_id': False, 'gene_set_library':True})
		er_pendings = mongo.db['enrichr_temp'].find({'dataset_id': dataset_id}, 
			{'_id': False, 'gene_set_library':True})

		ds.visualizations = visualizations
		ds.enrichment_results = [er for er in enrichments]
		er_pendings = Counter([er['gene_set_library'] for er in er_pendings])
		ds.er_pendings = [{'gene_set_library': key, 'count': val} for key, val in er_pendings.items()]	
		
		return render_template('progress.html', 
			ENTER_POINT=ENTER_POINT,
			logger_msg=Logger.get_all_msg(dataset_id),
			ds=ds)

@app.route(ENTER_POINT + '/graph_page/<string:dataset_id>/<string:graph_name>')
def graph_page(graph_name, dataset_id):
	return redirect(ENTER_POINT + '/graph_page/%s/%s/2' % (dataset_id, graph_name))

@app.route(ENTER_POINT + '/graph_page/<string:dataset_id>/<string:graph_name>/<int:n_dim>')
def graph_page_with_ndim(graph_name, dataset_id, n_dim):
	# defaults
	sdvConfig = {
		'labelKey': ['sample_id', 'title'],
	}
	if n_dim == 2:
		sdvConfig['is3d'] = False
		sdvConfig['pointSize'] = 12
	elif n_dim == 3:
		sdvConfig['is3d'] = True
		sdvConfig['pointSize'] = 0.5

	# pick the attributes for default shaping and coloring
	if dataset_id.startswith('GSE'):
		gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
	else:
		gds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
	n_samples = len(gds.sample_ids)
	d_col_nuniques = {}
	for col in gds.meta_df.columns:
		n_uniques = gds.meta_df[col].nunique()
		if n_uniques < n_samples:
			d_col_nuniques[col] = n_uniques

	d_col_nuniques = sorted(d_col_nuniques.items(), key=lambda x:x[1])

	if len(d_col_nuniques) == 0: 
		# color by clustering if no meta col properly group cells
		sdvConfig['colorKey'] = 'KMeans-clustering'
	else:
		sdvConfig['colorKey'] = d_col_nuniques[0][0]

	sdvConfig['shapeKey'] = None

	visualizations = get_available_vis(mongo.db, dataset_id)

	# flag indicating whether a tree will be plotted
	# has_tree = graph_name in PSEUDOTIME_ALGOS
	return render_template('index.html', 
		script='main',
		ENTER_POINT=ENTER_POINT,
		graphs=json.dumps(visualizations),
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
	'''Redirect to the next API with n_dim = 2 for backward compatibility.
	'''
	return redirect(ENTER_POINT + '/graph/%s/%s/2' % (dataset_id, graph_name))

@app.route(ENTER_POINT + '/graph/<string:dataset_id>/<string:graph_name>/<int:n_dim>', methods=['GET'])
def load_graph_layout_coords_with_dim(graph_name, dataset_id, n_dim):
	'''API for different graphs'''
	if request.method == 'GET':
		if dataset_id.startswith('GSE'):
			gds = GEODataset.load(dataset_id, mongo.db, meta_only=True)
		else:
			gds = GeneExpressionDataset.load(dataset_id, mongo.db, meta_only=True)
		
		if graph_name != 'PCA' and n_dim == 3:
			graph_name += '-3d'

		if graph_name not in PSEUDOTIME_ALGOS:
			vis = Visualization.load(dataset_id, graph_name, mongo.db, n_dim=n_dim)
			graph_df = load_vis_df(vis, gds)
		else:
			pe = PseudotimeEstimator.load(dataset_id, graph_name, mongo.db, n_dim=n_dim)
			graph_df = load_psudotime_df(pe, gds)
		return graph_df.reset_index().to_json(orient='records')


@app.route(ENTER_POINT + '/tree/<string:dataset_id>/<string:graph_name>/<int:n_dim>', methods=['GET'])
def load_psudotime_tree(graph_name, dataset_id, n_dim):
	'''API to retrieve the tree from psudotime estimation.
	'''
	if request.method == 'GET':
		scaler_range = (0, 20)
		if n_dim == 3:
			graph_name += '-3d'
			scaler_range = (-10, 10)
		# Load monocle results
		if PseudotimeEstimator.exists(dataset_id, graph_name, mongo.db):
			pe = PseudotimeEstimator.load(dataset_id, graph_name, mongo.db, n_dim=n_dim)
			if n_dim == 3:
				# Fit scalers based on n_dim
				scaler_z = MinMaxScaler(scaler_range).fit(pe.coords[:, 2].reshape(-1, 1))
			scaler_x = MinMaxScaler(scaler_range).fit(pe.coords[:, 0].reshape(-1, 1))
			scaler_y = MinMaxScaler(scaler_range).fit(pe.coords[:, 1].reshape(-1, 1))

			edge_df = pe.results['edge_df'].rename(columns={
				'source_prin_graph_dim_1': 'x', 
				'source_prin_graph_dim_2': 'y', 
				'source_prin_graph_dim_3': 'z',
				'target_prin_graph_dim_1': 'xe', 
				'target_prin_graph_dim_2': 'ye', 
				'target_prin_graph_dim_3': 'ze'
				})
			# Apply scaling
			for col in ['x', 'y', 'z', 'xe', 'ye', 'ze']:
				if col in edge_df.columns:
					if col.startswith('x'):
						edge_df[col] = scaler_x.transform(edge_df[col].values.reshape(-1, 1))[:, 0]
					elif col.startswith('y'):
						edge_df[col] = scaler_y.transform(edge_df[col].values.reshape(-1, 1))[:, 0]
					elif col.startswith('z'):
						edge_df[col] = scaler_z.transform(edge_df[col].values.reshape(-1, 1))[:, 0]

			return edge_df.to_json(orient='records')
		else: # no psudotime tree available
			abort(500)

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
Predicted labels search endpoints
'''
@app.route(ENTER_POINT + '/label/query/<string:dataset_id>/<string:query_string>', methods=['GET'])
def search_labels(query_string, dataset_id):
	if request.method == 'GET':
		docs = mongo.db['preds'].find(
			{'$and': [
				{'dataset_id': dataset_id},
				{'labels': {'$elemMatch': {'$regex': ".*%s.*" % query_string, '$options': 'i'} }}
			]}, 
			{'_id':False, 'labels': True, 'name':True})

		array_of_labels = []
		for doc in docs:
			for label in doc['labels']:
				if query_string.lower() in label.lower():
					label = {'name': doc['name'], 'term': label}
					array_of_labels.append(label)
		return jsonify(array_of_labels)

@app.route(ENTER_POINT + '/label/get/<string:dataset_id>/<string:label>', methods=['GET'])
def retrieve_label_probas(dataset_id, label):
	name = find_prediction_name_for_label(label, mongo.db)
	doc = Prediction.get_label_probas(dataset_id, name, label, mongo.db)
	return jsonify(doc)

'''
Most probable labels from a prediction
'''
@app.route(ENTER_POINT + '/prediction/query/<string:dataset_id>', methods=['GET'])
def get_predictions(dataset_id):
	if request.method == 'GET':
		'''Return a list of available predictions for the dataset'''
		docs = mongo.db['preds'].find({'dataset_id': dataset_id}, {'name':True, '_id':False})
		return jsonify([{'name': doc['name']} for doc in docs])

@app.route(ENTER_POINT + '/prediction/get/<string:dataset_id>/<string:pred_name>', methods=['GET'])
def retrieve_prediction_top_labels(dataset_id, pred_name):
	doc = Prediction.get_top_labels(dataset_id, pred_name, mongo.db)
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
	# dataset-level meta
	dataset_meta = gds.meta.copy()
	# remove redundant sample-level meta
	dataset_meta.pop('meta_df', None)
	dataset_meta.pop('sample_id', None)
	dataset_meta['id'] = dataset_id

	# get the idx of the sample in the dataset
	idx = gds.sample_ids.index(sample_id)

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
	cur = mongo.db['enrichr'].find({'$and': [
			{'dataset_id': dataset_id}, 
			{'scores': {'$exists': True}}
		]},
		{'gene_set_library':True, 'scores': True, '_id':False})
	for doc in cur:
		lib = doc['gene_set_library']
		recs = [{'term': term, 'score': scores[idx]} for term, scores in doc['scores'].iteritems()]
		sorted_scores = pd.DataFrame.from_records(recs).sort_values('score', na_position='first')
		top_terms = sorted_scores[-10:][::-1].to_dict(orient='records')
		enrichment[lib] = top_terms

	# prepare prediction
	prediction = {}
	cur = mongo.db['preds'].find({'dataset_id': dataset_id},
		{'name':True, 'probas': True, '_id':False})
	for doc in cur:
		pred = doc['name']
		recs = [{'term': label, 'score': probas[idx]} for label, probas in doc['probas'].iteritems()]
		sorted_probas = pd.DataFrame.from_records(recs).sort_values('score', na_position='first')
		top_labels = sorted_probas[-10:][::-1].to_dict(orient='records')
		prediction[pred] = top_labels

	sample_data = {
		'genes': 	top_up_genes + top_dn_genes,
		'enrichment': enrichment,
		'prediction': prediction
	}
	return render_template('sample_page.html', 
		sample_meta=sample_meta,
		dataset_meta=dataset_meta,
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
		{'gene':True, 'values': True, '_id': False},
		cursor_type=CursorType.EXHAUST
	)
	# pick to top expressed genes
	zscores_df = pd.DataFrame.from_dict({doc['gene'] : np.array(doc['values'])[mask] for doc in cur})
	sorted_zscores = np.median(zscores_df.values, axis=0)
	sorted_genes = zscores_df.columns[sorted_zscores.argsort()]
	top_up_genes = sorted_genes[-20:][::-1]
	top_dn_genes = sorted_genes[:20][::-1]
	top_genes = list(top_up_genes) + list(top_dn_genes)
	top_genes_zscores_df = zscores_df.loc[:, top_genes]

	# prepare enrichment
	enrichment = {}
	cur = mongo.db['enrichr'].find({'$and': [
			{'dataset_id': dataset_id}, 
			{'scores': {'$exists': True}}
		]},
		{'gene_set_library':True, 'scores': True, '_id':False},
		cursor_type=CursorType.EXHAUST)
	for doc in cur:
		lib = doc['gene_set_library']
		scores_df = pd.DataFrame.from_dict({term: np.array(scores)[mask] for term, scores in doc['scores'].iteritems() })\
			.fillna(0)
		sorted_scores = scores_df.median().sort_values(ascending=False, na_position='last')
		n = min(10, (sorted_scores>0).sum())
		top_terms = sorted_scores[:n].index
		top_terms_scores = scores_df.loc[:, top_terms].melt().to_dict(orient='list') # {term: [values]}
		enrichment[lib] = top_terms_scores

	# prepare prediction
	prediction = {}
	cur = mongo.db['preds'].find({'dataset_id': dataset_id}, 
		{'name':True, 'probas': True, '_id':False},
		cursor_type=CursorType.EXHAUST)
	for doc in cur:
		pred = doc['name']
		scores_df = pd.DataFrame.from_dict({label: np.array(probas)[mask] for label, probas in doc['probas'].iteritems() })\
			.fillna(0)
		sorted_scores = scores_df.median().sort_values(ascending=False, na_position='last')
		n = min(10, (sorted_scores>0).sum())
		top_labels = sorted_scores[:n].index
		top_labels_scores = scores_df.loc[:, top_labels].melt().to_dict(orient='list') # {label: [values]}
		prediction[pred] = top_labels_scores

	plot_data = { 
		'samples_meta': samples_meta.to_dict(orient='list'),
		'genes': top_genes_zscores_df.melt().to_dict(orient='list'), # {'gene': [genes], 'value': [values]}
		'enrichment' : enrichment,
		'prediction': prediction,
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
@app.errorhandler(500)
def error_json(e):
	return jsonify(error=500, text=str(e)), 500

from jinja2 import Markup
app.jinja_env.globals['include_raw'] = lambda filename : Markup(app.jinja_loader.get_source(app.jinja_env, filename)[0])


if __name__ == '__main__':
	# app.run(host='0.0.0.0', port=5000, threaded=True)
	socketio.run(app, host='0.0.0.0', port=5000)

