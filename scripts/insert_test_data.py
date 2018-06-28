'''
Insert some data into the MongoDB
'''
import sys
sys.path.append('../')
from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from classes import *

gene_set_libraries = ['KEGG_2016', 'ChEA_2016', 'KEA_2015',
	'ARCHS4_Cell-lines', 'ARCHS4_Tissues']

# gse = 'GSE96870'
# organism = 'mouse'
# gse = 'GSE68086'
# organism = 'human'

# gses = ['GSE57872', 'GSE75140']
# organisms = ['human'] * len(gses)

gses = ['GSE96630']
organisms = ['mouse']

for gse, organism in zip(gses, organisms):
	print 'Retrieving expression data from h5 for %s' % gse
	gds = GEODataset(gse_id=gse, organism=organism)
	print gds.df.shape


	print 'POSTing DEGs to Enrichr'
	d_sample_userListId = gds.post_DEGs_to_Enrichr(db)
	print len(d_sample_userListId)

	rid = gds.save(db)
	print rid


	for gene_set_library in gene_set_libraries:

		print 'Performing enrichment on: %s' % gene_set_library 
		er = EnrichmentResults(gds, gene_set_library)
		er.do_enrichment(db)
		er.summarize(db)
		print er.save(db)
		er.remove_intermediates(db)


	print 'Performing PCA'
	vis = Visualization(ged=gds, name='PCA', func=do_pca)
	coords = vis.compute_visualization()
	print vis.save(db)

	print 'Performing tSNE'
	vis = Visualization(ged=gds, name='tSNE', func=do_tsne)
	coords = vis.compute_visualization()
	print vis.save(db)
