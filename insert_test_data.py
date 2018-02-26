'''
Insert some data into the MongoDB
'''

from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from classes import *

gse = 'GSE96870'
organism = 'mouse'

gds = GEODataset(gse_id=gse, organism='mouse')
print gds.df.shape

rid = gds.save(db)
print rid

d_sample_userListId = gds.post_DEGs_to_Enrichr()
print len(d_sample_userListId)
er = EnrichmentResults(gds, 'KEGG_2016')
er.do_enrichment(db)
er.summarize(db)
print er.save(db)

db['enrichr_temp'].remove({'$and': [
				{'sample_id': {'$in': er.ged.sample_ids.tolist()}},
				{'gene_set_library': er.gene_set_library}
			]})

from sklearn.decomposition import PCA

def do_pca(X):
	pca = PCA(n_components=2)
	return pca.fit_transform(X)

vis = Visualization(ged=gds, name='PCA', func=do_pca)
coords = vis.compute_visualization()
print vis.save(db)
