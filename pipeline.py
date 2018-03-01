'''This is the pipeline for uploaded dataset, including the following steps:
1) retrieving the dataset by ID,
2) compute visualizations
3) perform enrichment
'''

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--id', help='Dataset ID', required=True)
parser.add_argument('-g', '--gsl', help='Gene set libraries (comma separated strings)', 
	default='KEGG_2016,ARCHS4_Cell-lines')

args = parser.parse_args()

dataset_id = args.id
gene_set_libraries = args.gsl.split(',')


from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from classes import *

# step 1.
print 'Retrieving expression data from database for %s' % dataset_id
gds = GeneExpressionDataset.load(dataset_id, db, meta_only=False)
print 'Dataset loaded:', gds.df.shape

# step 2.
print 'Performing PCA'
vis = Visualization(ged=gds, name='PCA', func=do_pca)
coords = vis.compute_visualization()
print vis.save(db)

print 'Performing tSNE'
vis = Visualization(ged=gds, name='tSNE', func=do_tsne)
coords = vis.compute_visualization()
print vis.save(db)

# step 3.
print 'POSTing DEGs to Enrichr'
d_sample_userListId = gds.post_DEGs_to_Enrichr(db)
print len(d_sample_userListId)

for gene_set_library in gene_set_libraries:
	print 'Performing enrichment on: %s' % gene_set_library 
	er = EnrichmentResults(gds, gene_set_library)
	er.do_enrichment(db)
	er.summarize(db)
	print er.save(db)
	er.remove_intermediates(db)

