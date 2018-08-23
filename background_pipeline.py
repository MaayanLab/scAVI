import os
import logging
from cStringIO import StringIO

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def background_pipeline_test(socketio=None, namespace='/test'):
    """Example of how to send server generated events to clients."""
    count = 0
    for i in range(100):
        socketio.sleep(1)
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': i},
                      namespace=namespace,
                      # broadcast=True
                      )


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
		self.log_fp = os.path.join(SCRIPT_DIR, 'data/logs', '%s.log'%dataset_id)
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
		log_fp = os.path.join(SCRIPT_DIR, 'data/logs', '%s.log'%dataset_id)
		msg = ''
		if os.path.isfile(log_fp):
			msg = open(log_fp, 'r').read()

		return msg.strip().split('\n')
		

def background_pipeline(socketio=None, dataset_id=None, gene_set_libraries=None, logger=None):

	gene_set_libraries = gene_set_libraries.split(',')

	from database import *
	from pymongo import MongoClient
	mongo = MongoClient(MONGOURI)

	db = mongo['SCV']
	coll = db['dataset']

	from classes import *

	# logger = setup_logger(dataset_id)

	def emit_message(msg='', socketio=socketio, namespace='/%s'%dataset_id, logger=logger):
		logger.info(msg)
		# get the last message from stream handler of the logger
		log_msg = logger.get_last_msg()
		socketio.emit('my_response', 
				{'data': log_msg},
				namespace=namespace)

	# step 1.
	emit_message('Retrieving expression data from database for %s' % dataset_id)

	gds = GeneExpressionDataset.load(dataset_id, db, meta_only=False)
	emit_message('Dataset loaded with shape %d x %d' % gds.df.shape)

	# step 2.
	emit_message('Performing PCA')
	vis = Visualization(ged=gds, name='PCA', func=do_pca)
	coords = vis.compute_visualization()
	emit_message('PCA finished')
	vis.save(db)

	emit_message('Performing tSNE-2d')
	vis = Visualization(ged=gds, name='tSNE', func=do_tsne, n_components=2)
	coords = vis.compute_visualization()
	emit_message('tSNE-2d finished')
	vis.save(db)

	emit_message('Performing tSNE-3d')
	vis = Visualization(ged=gds, name='tSNE-3d', func=do_tsne)
	coords = vis.compute_visualization()
	emit_message('tSNE-3d finished')
	vis.save(db)

	# step 3.
	emit_message('POSTing DEGs to Enrichr')
	d_sample_userListId = gds.post_DEGs_to_Enrichr(db)
	emit_message('Number of gene sets POSTed: %d' % len(d_sample_userListId))

	for gene_set_library in gene_set_libraries:
		emit_message('Performing enrichment on: %s' % gene_set_library)
		er = EnrichmentResults(gds, gene_set_library)
		er.do_enrichment(db)
		er.summarize(db)
		er.save(db)
		emit_message('Enrichment on %s has finished' % gene_set_library)
		er.remove_intermediates(db)

	emit_message('All completed!')
	