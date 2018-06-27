'''
This script check the completeness of all GEO datasets in the MongoDB, 
and perform analyses to get the vis/enrichr results if anything is missing.

'''

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-g', '--gsl', help='Gene set libraries (comma separated strings)', 
	default='KEGG_2016,ARCHS4_Cell-lines')

# predict pathways and upstream regulators:
# 'ChEA_2016,KEA_2015,KEGG_2016'
# predict cell type and tissue
# 'ARCHS4_Cell-lines,ARCHS4_Tissues'

parser.add_argument('-v', '--vis', help='Visualizations (comma separated strings)', 
	default='PCA,tSNE')

args = parser.parse_args()

gene_set_libraries = args.gsl.split(',')
visualization_names = args.vis.split(',')

import sys
sys.path.append('../')

from database import *
from pymongo import MongoClient

MONGOURI='mongodb://146.203.54.131:27017/SCV'
mongo = MongoClient(MONGOURI)

db = mongo['SCV']

from classes import *

vis_funcs = {
	'PCA': do_pca,
	'tSNE': do_tsne
}

# find existing GEO datasets in the DB
existing_GSE_ids = filter(lambda x: x.startswith('GSE'), db['dataset'].distinct('id'))

print 'Number of GSEs in the database: %d' % len(existing_GSE_ids)

for c, gse_id in enumerate(existing_GSE_ids):
	is_complete = True

	# get available visualizations in the DB
	cur = db['vis'].find({'dataset_id': gse_id}, 
		{'_id':False, 'name':True})
	visualizations = [doc['name'] for doc in cur]

	# get available enrichr results in the DB
	cur = db['enrichr'].find({'dataset_id': gse_id}, 
		{'_id':False, 'gene_set_library':True})
	gene_sets_avail = [doc['gene_set_library'] for doc in cur]

	if set(visualizations) != set(visualization_names):
		is_complete = False

	if set(gene_sets_avail) != set(gene_set_libraries):
		is_complete = False

	if not is_complete:
		print 'loading dataset %s' % gse_id
		gds = GEODataset.load(gse_id, db)
		print 'dataset shape: ', gds.df.shape

		for vis_name in set(visualization_names) - set(visualizations):
			print 'Performing %s for dataset %s' % (vis_name, gse_id)
			vis = Visualization(ged=gds, name=vis_name, func=vis_funcs[vis_name])
			coords = vis.compute_visualization()
			vis.save(db)
			print 'Finished %s for dataset %s' % (vis_name, gse_id)
	
		if set(gene_sets_avail) != set(gene_set_libraries):
			print 'POSTing DEGs to Enrichr'
			d_sample_userListId = gds.post_DEGs_to_Enrichr(db)
			print len(d_sample_userListId)

			for gene_set_name in set(gene_set_libraries) - set(gene_sets_avail):
				print 'Performing enrichment analysis on %s for dataset %s' % (gene_set_name, gse_id)
				er = EnrichmentResults(gds, gene_set_name)
				er.do_enrichment(db)
				er.summarize(db)
				print 'Finished enrichment analysis on %s for dataset %s' % (gene_set_name, gse_id)
				print er.save(db)
				er.remove_intermediates(db)


