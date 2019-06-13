import sys
from pymongo import MongoClient
sys.path.append('../')
from models import *

mongo = MongoClient(MONGOURI)
db = mongo['SCV']


etype = 'samplewise-z'
# etype = 'background-bulk'
# genes_meta = pd.read_csv('../../scMeta/scripts/results/human_bulkRNAseq_gene_stats_df.csv').set_index('gene')

gene_set_libraries = ['KEGG_2016', 'ARCHS4_Tissues']
gse_id = 'GSE111727'
gds = GEODataset.load(gse_id, db, meta_only=False)


if not gds.DEGs_posted(db, etype=etype):
	print 'POSTing DEGs to Enrichr'
	d_sample_userListId = gds.post_DEGs_to_Enrichr(db, etype=etype)
	gds.save_DEGs(db, etype=etype)
else:
	d_sample_userListId = gds.post_DEGs_to_Enrichr(db, etype=etype)

# get available enrichr results in the DB
cur = db['enrichr'].find({'$and': [
		{'dataset_id': gse_id}, 
		{'type': etype}
	]},
	{'_id':False, 'gene_set_library':True})
gene_sets_avail = [doc['gene_set_library'] for doc in cur]

for gene_set_name in set(gene_set_libraries) - set(gene_sets_avail):
	print 'Performing enrichment analysis on %s for dataset %s' % (gene_set_name, gse_id)
	er = EnrichmentResults(gds, gene_set_name, etype=etype)
	# try:
	er.do_enrichment(db)
	er.summarize(db)
	print 'Finished enrichment analysis on %s for dataset %s' % (gene_set_name, gse_id)
	print er.save(db)
	er.remove_intermediates(db)
