'''
Insert scRNA-seq data from GEO into the MongoDB
'''

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-g', '--gsl', help='Gene set libraries (comma separated strings)', 
	default='KEGG_2016,KEA_2015')
parser.add_argument('-v', '--vis', help='Visualizations (comma separated strings)', 
	default='PCA,tSNE,tSNE-3d')
parser.add_argument('-i', '--input', help='Input csv file with columns `GSE` and `organism`', 
	default='')
parser.add_argument('-t', '--cpu', help='Number of CPUs to use', 
	default=1)

import sys
sys.path.append('../')
from joblib import Parallel, delayed
from models.database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from models import *

args = parser.parse_args()
gene_set_libraries = args.gsl.split(',')
visualization_names = args.vis.split(',')
input_file = args.input
n_cpus = int(args.cpu)

input_df = pd.read_csv(input_file)
print '# GSEs in %s: %d' %(input_file, input_df.shape[0])

vis_funcs = {
	'PCA': do_pca,
	'tSNE-3d': do_tsne,
	'tSNE': lambda x: do_tsne(x, n_components=2)
}

# Get a list of existing GSEs in the DB
existing_GSE_ids = filter(lambda x: x.startswith('GSE'), db['dataset'].distinct('id'))

input_df = input_df.loc[~input_df['GSE'].isin(existing_GSE_ids)]
print '# GSEs in %s to insert: %d' %(input_file, input_df.shape[0])

# Shuffle rows
input_df = input_df.sample(frac=1)

gses = input_df['GSE']
organisms = input_df['organism']

def inner_func(gse_id, organism):
	print 'Retrieving expression data from h5 for %s' % gse_id
	try:
		gds = GEODataset(gse_id=gse_id, organism=organism)
	except RuntimeError as e:
		print e
		pass
	else:
		print gds.df.shape
		if gds.df.shape[1] > 30:

			# print 'POSTing DEGs to Enrichr'
			# d_sample_userListId = gds.post_DEGs_to_Enrichr(db)
			# print len(d_sample_userListId)

			rid = gds.save(db)
			print 'Dataset %s saved to DB' % gse_id
			print rid

			for vis_name in visualization_names:
				print 'Performing %s for dataset %s' % (vis_name, gse_id)
				vis = Visualization(ged=gds, name=vis_name, func=vis_funcs[vis_name])
				coords = vis.compute_visualization()
				vis.save(db)
				print 'Finished %s for dataset %s' % (vis_name, gse_id)

			# for gene_set_library in gene_set_libraries:
			# 	print 'Performing enrichment analysis on %s for dataset %s' % (gene_set_library, gse_id)
			# 	er = EnrichmentResults(gds, gene_set_library)
			# 	try:
			# 		er.do_enrichment(db)
			# 		er.summarize(db)
			# 		print 'Finished enrichment analysis on %s for dataset %s' % (gene_set_library, gse_id)
			# 		print er.save(db)
			# 		er.remove_intermediates(db)
			# 	except:
			# 		pass
	return

if n_cpus == 1:
	for gse_id, organism in zip(gses, organisms):
		try:
			inner_func(gse_id, organism)
		except Exception as e:
			print e
			pass

else:
	Parallel(n_jobs=n_cpus, 
		backend='multiprocessing',
		verbose=10
		)(delayed(inner_func(gse_id, organism)) for gse_id, organism in zip(gses, organisms))
