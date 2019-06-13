'''
This script check the completeness of all GEO datasets in the MongoDB, 
and perform analyses to get the vis/enrichr results if anything is missing.

'''
import os
import argparse
import pandas as pd
parser = argparse.ArgumentParser()
parser.add_argument('-g', '--gsl', help='Gene set libraries (comma separated strings)', 
	default='KEGG_2016,ARCHS4_Tissues,ChEA_2016')
parser.add_argument('-e', '--etype', help='Enrichment type', 
	default='samplewise-z')

# predict pathways and upstream regulators:
# 'ChEA_2016,KEA_2015,KEGG_2016'
# predict cell type and tissue
# 'ARCHS4_Cell-lines,ARCHS4_Tissues'

parser.add_argument('-v', '--vis', help='Visualizations (comma separated strings)', 
	default='PCA,tSNE')

args = parser.parse_args()

gene_set_libraries = args.gsl.split(',')
etype = args.etype
visualization_names = args.vis.split(',')

if etype == 'background-z':
	SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
	meta_file_path = os.path.abspath(os.path.join(SCRIPT_DIR, '../../scMeta/scripts/results'))

	genes_meta_human = pd.read_csv(os.path.join(meta_file_path, 'human_scRNAseq_gene_stats_df.csv'))\
		.set_index('gene')[['mean_cpm', 'std_cpm']]
	genes_meta_mouse = pd.read_csv(os.path.join(meta_file_path, 'mouse_scRNAseq_gene_stats_df.csv'))\
		.set_index('gene')[['mean_cpm', 'std_cpm']]
	print 'Background files loaded:', genes_meta_human.shape, genes_meta_mouse.shape


import sys
sys.path.append('../')

from models.database import *
from pymongo import MongoClient

MONGOURI='mongodb://146.203.54.131:27017/SCV'
mongo = MongoClient(MONGOURI)

db = mongo['SCV']

from models import *

vis_funcs = {
	'PCA': do_pca,
	'tSNE': do_tsne
}

# find existing GEO datasets in the DB
existing_GSE_ids = db['dataset'].find(
	{'$and': [
		{'id': {'$regex': r'^GSE'}},
		{'sample_ids.30': {'$exists': True}}
	]}).distinct('id')


print 'Number of GSEs in the database: %d' % len(existing_GSE_ids)

for c, gse_id in enumerate(existing_GSE_ids):
	is_complete = True

	# get available visualizations in the DB
	cur = db['vis'].find({'dataset_id': gse_id}, 
		{'_id':False, 'name':True})
	visualizations = [doc['name'] for doc in cur]

	# get available enrichr results in the DB
	cur = db['enrichr'].find({'$and': [
			{'dataset_id': gse_id}, 
			{'type': etype}
		]},
		{'_id':False, 'gene_set_library':True})
	gene_sets_avail = [doc['gene_set_library'] for doc in cur]

	if not set(visualization_names).issubset(set(visualizations)):
		is_complete = False

	if not set(gene_set_libraries).issubset(set(gene_sets_avail)):
		is_complete = False

	if not is_complete:
		print 'loading dataset %s' % gse_id
		gds = GEODataset.load(gse_id, db)
		print 'dataset shape: ', gds.df.shape
		if gds.df.shape[1] > 30:

			for vis_name in set(visualization_names) - set(visualizations):
				print 'Performing %s for dataset %s' % (vis_name, gse_id)
				vis = Visualization(ged=gds, name=vis_name, func=vis_funcs[vis_name])
				coords = vis.compute_visualization()
				vis.save(db)
				print 'Finished %s for dataset %s' % (vis_name, gse_id)
		
			if set(gene_sets_avail) != set(gene_set_libraries):
				if not gds.DEGs_posted(db, etype=etype):
					print 'POSTing DEGs to Enrichr'
					genes_meta = None
					if etype == 'background-z':
						if gds.organism == 'human':
							genes_meta = genes_meta_human
						else:
							genes_meta = genes_meta_mouse
					d_sample_userListId = gds.post_DEGs_to_Enrichr(db, etype=etype, genes_meta=genes_meta)
					gds.save_DEGs(db, etype=etype)
				else:
					d_sample_userListId = gds.post_DEGs_to_Enrichr(db, etype=etype)

				print d_sample_userListId.keys(), len(d_sample_userListId[etype])

				for gene_set_name in set(gene_set_libraries) - set(gene_sets_avail):
					print 'Performing enrichment analysis on %s for dataset %s' % (gene_set_name, gse_id)
					er = EnrichmentResults(gds, gene_set_name, etype=etype)
					try:
						er.do_enrichment(db)
						er.summarize(db)
						print 'Finished enrichment analysis on %s for dataset %s' % (gene_set_name, gse_id)
						print er.save(db)
						er.remove_intermediates(db)
					except Exception as e:
						print e
						# pass


