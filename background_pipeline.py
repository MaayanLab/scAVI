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


def background_pipeline(socketio=None, dataset_id=None, gene_set_libraries=None):

	gene_set_libraries = gene_set_libraries.split(',')

	from database import *
	from pymongo import MongoClient
	mongo = MongoClient(MONGOURI)

	db = mongo['SCV']
	coll = db['dataset']

	from classes import *

	def emit_message(msg='', socketio=socketio, namespace='/%s'%dataset_id):
		socketio.emit('my_response', 
				{'data': msg},
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

	emit_message('Performing tSNE')
	vis = Visualization(ged=gds, name='tSNE', func=do_tsne)
	coords = vis.compute_visualization()
	emit_message('tSNE finished')
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
	