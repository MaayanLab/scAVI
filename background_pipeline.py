import os
import time
import logging
from cStringIO import StringIO
from upload_utils import *
from models import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

class Logger(object):
	"""A custom logger"""
	def __init__(self, dataset_id):
		super(Logger, self).__init__()
		self.dataset_id = dataset_id
		# create logger
		log_capture_string = StringIO()
		self.logger = logging.getLogger(dataset_id)
		self.logger.setLevel(logging.INFO)
		# create file handler and stream handler for the logger
		self.log_fp = os.path.join(SCRIPT_DIR, 'logs', '%s.log'%dataset_id)
		fh = logging.FileHandler(self.log_fp)
		fh.setLevel(logging.INFO)
		ch = logging.StreamHandler(log_capture_string)
		ch.setLevel(logging.INFO)

		# create formatter and add it to the handlers
		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		fh.setFormatter(formatter)
		self.logger.addHandler(fh)
		ch.setFormatter(formatter)
		self.logger.addHandler(ch)

	def info(self, msg):
		self.logger.info(msg)

	def get_last_msg(self):
		stream = self.logger.handlers[-1].stream
		return stream.getvalue().strip().split('\n')[-1]

	@classmethod
	def get_all_msg(self, dataset_id):
		log_fp = os.path.join(SCRIPT_DIR, 'logs', '%s.log'%dataset_id)
		msg = ''
		if os.path.isfile(log_fp):
			msg = open(log_fp, 'r').read()
		return msg.strip().split('\n')


def _emit_message(msg='', socketio=None, namespace='/', logger=None, 
	**kwargs):
	done = kwargs.get('done', False)
	if not done: # only log message where done is False
		logger.info(msg)
		# get the last message from stream handler of the logger
		log_msg = logger.get_last_msg()
		kwargs['data'] = log_msg
	kwargs['done'] = done
	socketio.emit('my_response', 
		kwargs,
		namespace=namespace)


def background_preprocess_test_pipeline(socketio=None, upload_id=None, enter_point=None, logger=None):
	'''For testing only.''' 
	def emit_message(msg='', **kwargs):
		_emit_message(msg=msg, socketio=socketio, namespace='%s/%s'%(enter_point, upload_id), logger=logger, **kwargs)

	upload_obj = Upload.load(upload_id)
	emit_message('before the loop')
	print 'before the loop'
	for i in range(10):
		emit_message('tick %d from upload_id: %s, finished? %s' % (i, upload_obj.id, upload_obj.done))
		print 'tick %d from upload_id: %s, finished? %s' % (i, upload_obj.id, upload_obj.done)
		time.sleep(5)

	dataset_id = 'some_data_id'
	emit_message(done=True, dataset_id=dataset_id)
	upload_obj.finish(dataset_id)
	emit_message('tick %d from upload_id: %s, finished? %s' % (i, upload_obj.id, upload_obj.done))


def background_preprocess_pipeline(socketio=None, upload_id=None, enter_point=None, logger=None):
	'''Pipeline for preprocessing uploaded files.'''
	def emit_message(msg='', **kwargs):
		_emit_message(msg=msg, socketio=socketio, namespace='%s/%s'%(enter_point, upload_id), logger=logger, **kwargs)

	upload_obj = Upload.load(upload_id)
	time.sleep(1)
	emit_message('Parsing the uploaded files: %s' % ', '.join(upload_obj.files.values()))
	try:
		expr_df, meta_df = upload_obj.parse()
	except Exception as e:
		upload_obj.catch_error(e)
		error_message = get_exception_message(e)
		emit_message(msg=error_message, error=True, e=error_message)
	else:
		emit_message('Files parsing files with shapes: %s, %s' % (str(expr_df.shape), str(meta_df.shape)))
		emit_message('Determining the data type of the gene expression file...')

	# Only do filtering for sparse expr_df
	meta_df_cols = set(meta_df.columns)
	if 'n_reads' in meta_df_cols and 'n_expressed_genes' in meta_df_cols:
		emit_message('Filtering out low quality cells')
		cell_mask = (meta_df['n_reads'] > 2000) & (meta_df['n_expressed_genes'] > 500)
		meta_df = meta_df.loc[cell_mask]
		expr_df = expr_df.loc[:, cell_mask]
		emit_message('Data after filtering have shapes: %s' % str(expr_df.shape))

	try:
		expr_dtype = expression_is_valid(expr_df)
	except ValueError as e:
		
		emit_message('Gene expression data file is not valid:')
		upload_obj.catch_error(e)
		error_message = get_exception_message(e)
		emit_message(msg=error_message, error=True, e=error_message)
	else:
		# replace '.' to prevent MongoDB error
		meta_df.columns = meta_df.columns.map(lambda x: x.replace('.', '_'))
		emit_message('Expression data type is: %s' % expr_dtype)
		emit_message('Packaging dataset to HDF5 file...')
		h5_file = upload_obj.build_h5(expr_df, meta_df)
		emit_message('Uploading dataset to Google Cloud...')
		upload_obj.upload_h5_to_cloud(h5_file)
		emit_message('Dataset is uploaded to Google Cloud', upload_id=upload_id)

		if expr_dtype == 'counts':
			emit_message('Computing CPMs for read counts...')
			expr_df = compute_CPMs(expr_df)
			emit_message('Finished computing CPMs')

		emit_message('Converting dataset into GeneExpressionDataset object...')
		dataset = GeneExpressionDataset(expr_df, meta={'meta_df': meta_df.to_dict('list')})
		emit_message('Converted GeneExpressionDataset object')
		# check if dataset exists
		if not dataset.exists(Upload.db):
			# emit_message('Normalizing dataset...')
			# dataset.log10_and_zscore()
			# emit_message('Finished data normalization')
			dataset.save(Upload.db)
			emit_message('Dataset(%s) has been saved into the database' % dataset.id)
		else:
			emit_message('Dataset(%s) already exists in the database' % dataset.id)

		emit_message(done=True, dataset_id=dataset.id)
		upload_obj.finish(dataset.id)


def background_pipeline(socketio=None, dataset_id=None, enter_point=None, gene_set_libraries=None, logger=None, db=None):
	'''Pipeline for running DR, enrichment and etc. for dataset already saved in the db.'''
	def emit_message(msg='', **kwargs):
		_emit_message(msg=msg, socketio=socketio, namespace='%s/%s'%(enter_point, dataset_id), logger=logger, **kwargs)

	gene_set_libraries = gene_set_libraries.split(',')
	time.sleep(1)
	# step 1.
	emit_message('Retrieving expression data from database for %s' % dataset_id)
	gds = GeneExpressionDataset.load(dataset_id, db, meta_only=False)
	emit_message('Dataset loaded with shape (%d x %d)' % gds.df.shape)
	visualized = db['vis'].find({'dataset_id': dataset_id},{"name":True})
	vis_num = visualized.count()
	vis_done = []
	for v in visualized:
		vis_done.append(v["name"])
	vis_num = db['vis'].find({'dataset_id': dataset_id}, {'name':True}).count()
	enriched = db['enrichr'].find({'dataset_id': dataset_id},{"gene_set_library": True})
	enrich_num = enriched.count()
	enriched_libraries = []
	for lib in enriched:
		enriched_libraries.append(lib["gene_set_library"])
	emit_message('Dataset has %d visualizations and  %d enrichments' % (vis_num, enrich_num))
	# Check if visualizations exists:
	# step 2.
	if 'PCA' not in vis_done:
		emit_message('Performing PCA...')
		vis = Visualization(ged=gds, name='PCA', func=do_pca)
		coords = vis.compute_visualization()
		emit_message('PCA finished')
		emit_message(done='visualization', name='PCA')
		vis.save(db)
	else:
		emit_message("PCA is done")

	if 'tSNE' not in vis_done:
		emit_message('Performing tSNE-2d...')
		vis = Visualization(ged=gds, name='tSNE', func=do_tsne, n_components=2)
		coords = vis.compute_visualization()
		emit_message('tSNE-2d finished')
		emit_message(done='visualization', name='tSNE-2')
		vis.save(db)
	else:
		emit_message("tSNE-2d is done")

	if 'tSNE-3d' not in vis_done:
		emit_message('Performing tSNE-3d...')
		vis = Visualization(ged=gds, name='tSNE-3d', func=do_tsne)
		coords = vis.compute_visualization()
		emit_message('tSNE-3d finished')
		emit_message(done='visualization', name='tSNE-3')
		vis.save(db)
	else:
		emit_message("tSNE-3d is done")
	
	# if 'monocle' not in vis_done:
	# 	emit_message('Performing Monocle-2d...')
	# 	pe = PseudotimeEstimator(gds, name='monocle', func=lambda x: run_monocle_pipeline(x, n_components=2))
	# 	try:
	# 		pe.fit()
	# 	except RRuntimeError as e:
	# 		emit_message(get_exception_message(e))
	# 		pass
	# 	else:
	# 		emit_message('Monocle analysis finished')
	# 		emit_message(done='visualization', name='monocle-2')
	# 		pe.save(db)
	# else:
	# 	emit_message("monocle is done")
	
	if enrich_num < len(gene_set_libraries):
		# step 3.
		emit_message('POSTing DEGs to Enrichr for enrichment analysis')
		d_sample_userListId = gds.post_DEGs_to_Enrichr(db)
		emit_message('Number of gene sets sent to Enrichr: %d' % len(d_sample_userListId))
		emit_message('Will perform enrichment analysis on the following gene-set libraries: %s' % ', '.join(gene_set_libraries))
		for gene_set_library in gene_set_libraries:
			if gene_set_library not in enriched_libraries:
				emit_message('Performing enrichment on: %s' % gene_set_library)
				er = EnrichmentResults(gds, gene_set_library)
				er.do_enrichment(db)
				emit_message('Summarizing enrichment results from individual cells...')
				er.summarize(db)
				er.save(db)
				emit_message('Enrichment on %s has finished' % gene_set_library)
				emit_message(done='enrichment', name=gene_set_library)
				er.remove_intermediates(db)
			else:
				emit_message("Already enriched  for %s"%gene_set_library)
	else:
		emit_message('Enrichment complete, skipping')

	emit_message('All completed!')
	gds.finish(db)
