'''Utils for gene expression
'''
import os, sys
import json
import hashlib
import math
from collections import OrderedDict
import h5py
import requests
import numpy as np
import pandas as pd
from bson.codec_options import CodecOptions

from geo_meta import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def load_read_counts_and_meta(organism='human', gsms=[], gse=None, retrive_meta=True):
	'''Load data from h5 file using a list of GSMs or a GSE.
	'''
	fn = os.path.join(SCRIPT_DIR, 'data/%s_matrix.h5' % organism)
	f = h5py.File(fn, 'r')
	mat = f['data']['expression']
	genes = f['meta']['genes']
	# to prevent MongoDB error
	genes = map(lambda x:x.replace('.', '_'), genes)
	all_gsms = f['meta']['Sample_geo_accession']
	if gse is None:
		sample_mask = np.in1d(all_gsms, gsms)
		
	else:
		all_gses = f['meta']['Sample_series_id']
		sample_mask = np.in1d(all_gses, [gse])

	sample_ids = all_gsms[sample_mask]
	# Retrieve gene by sample matrix
	expr_df = pd.DataFrame(mat[sample_mask, :].T, index=genes, columns=sample_ids)

	# Filter out non-expressed genes
	expr_df = expr_df.loc[expr_df.sum(axis=1) > 0, :] 

	# Filter out samples with very low read counts
	valid_sample_mask = expr_df.sum(axis=0) > 100
	expr_df = expr_df.loc[:, valid_sample_mask]

	meta_doc = None
	if retrive_meta:
		## !! deprecate this part. will retrieve the meta from GEO directly using geo_query
		# Retrieve metadata
		meta_doc = {'meta_df':{}} 
		for meta_key in f['meta'].keys():
			if meta_key != 'genes':
				meta_vals = f['meta'][meta_key][sample_mask][valid_sample_mask]
				if len(np.unique(meta_vals)) == 1:
					meta_doc[meta_key] = meta_vals[0]
				else:
					meta_doc['meta_df'][meta_key] = list(meta_vals) 

	return expr_df, meta_doc


def compute_CPMs(expr_df, CPM_cutoff=0.3, at_least_in_persent_samples=10):
	'''Convert expression counts to CPM.
	'''
	n_samples = expr_df.shape[1]
	at_least_in_n_samples = int(math.ceil(at_least_in_persent_samples/100. * n_samples))

	expr_df = (expr_df * 1e6) / expr_df.sum(axis=0)
	# Filter out lowly expressed genes
	mask_low_vals = (expr_df > CPM_cutoff).sum(axis=1) > at_least_in_n_samples
	expr_df = expr_df.loc[mask_low_vals, :]
	return expr_df


def log10_and_zscore(expr_df):
	expr_df = np.log10(expr_df + 1.)
	expr_df = expr_df.apply(lambda x: (x-x.mean())/x.std(ddof=0), axis=1)
	return expr_df


def post_genes_to_enrichr(genes, description):
	genes_str = '\n'.join(genes)
	payload = {
		'list': (None, genes_str),
		'description': description
	}
	resp = requests.post('http://amp.pharm.mssm.edu/Enrichr/addList', files=payload)
	if not resp.ok:
		return None
	else:
		data = json.loads(resp.text)
		return data['userListId']


class GeneExpressionDataset(object):
	"""docstring for GeneExpressionDataset"""
	coll = 'dataset'
	coll_expr = 'expression'
	def __init__(self, df, enrichment_results=[], visualizations=[], meta={}):
		self.df = df # df could be CPMs/RPKMs/FPKMs/TPMs or z-scores.
		# assert not self.is_zscored()
		self.avg_expression = df.mean(axis=1)
		self.sample_ids = df.columns
		self.genes = df.index
		self.enrichment_results = enrichment_results
		self.visualizations = visualizations
		self.meta = meta
		self.meta_df = pd.DataFrame(meta.get('meta_df', {})).set_index(self.sample_ids)
		self.id = hashlib.md5(self.df.values.tobytes()).hexdigest()
	
	def log10_and_zscore(self):
		self.df = log10_and_zscore(self.df)

	def is_zscored(self):
		return self.df.min().min() < 0

	def DEGs_posted(self, db):
		'''Whether DEGs has been POSTed to Enrichr.'''
		result = False
		if hasattr(self, 'd_sample_userListId'):
			result = True
		else:
			doc = db[self.coll].find_one({'id': self.id}, 
				{'d_sample_userListId':True, '_id':False})
			if doc:
				result = len(doc.get('d_sample_userListId', {})) > 0
		return result

	def identify_DEGs(self, cutoff=2.33):
		if not self.is_zscored():
			self.log10_and_zscore()
		up_DEGs_df = self.df > cutoff
		return up_DEGs_df

	def post_DEGs_to_Enrichr(self, db, cutoff=2.33):
		if not self.DEGs_posted(db):
			up_DEGs_df = self.identify_DEGs(cutoff)
			d_sample_userListId = OrderedDict()

			for sample_id in self.sample_ids:
				up_genes = self.genes[np.where(up_DEGs_df[sample_id])[0]].tolist()
				user_list_id = None
				if len(up_genes) > 10:
					user_list_id = post_genes_to_enrichr(up_genes, '%s up' % sample_id)

				d_sample_userListId[sample_id] = user_list_id

		else:
			doc = db[self.coll].find_one({'id': self.id},
				{'d_sample_userListId':True, '_id':False},
				# as_class=OrderedDict
				codec_options=CodecOptions(OrderedDict)
				)
			d_sample_userListId = doc['d_sample_userListId']

		self.d_sample_userListId = d_sample_userListId
		return d_sample_userListId


	def save(self, db):
		if hasattr(self, 'd_sample_userListId'): 
			d_sample_userListId = self.d_sample_userListId
		else:
			d_sample_userListId = OrderedDict()
		doc = {
			'id': self.id,
			'meta': self.meta,
			'sample_ids': self.sample_ids.tolist(),
			'genes': self.genes.tolist(),
			'avg_expression': self.avg_expression.tolist(),
			'd_sample_userListId': d_sample_userListId
		}
		insert_result = db[self.coll].insert_one(doc)
		gene_expression_docs = [
			{'dataset_id': self.id, 'gene': gene, 'values': values.tolist()} for gene, values in self.df.iterrows()
		]
		_ = db[self.coll_expr].insert(gene_expression_docs)
		return insert_result.inserted_id

	def exists(self, db):
		doc = db[self.coll].find_one({'id': self.id})
		return doc is not None

	@classmethod
	def load(cls, dataset_id, db, meta_only=False):
		'''Load from the database.'''
		doc = db[cls.coll].find_one({'id': dataset_id}, {'_id':False})
		if doc is None:
			obj = None
		else:
			if meta_only:
				# fake a df
				df = pd.DataFrame(index=doc['genes'], columns=doc['sample_ids'])
			else:
				# retrieve gene expression from expression collection
				expressions = db[cls.coll_expr].find({'dataset_id': dataset_id}, 
					{'_id':False, 'gene':True, 'values':True})
				df = pd.DataFrame({expr['gene']: expr['values'] for expr in expressions}).transpose()
				df.columns = doc['sample_ids']
			obj = cls(df, meta=doc['meta'])
			if meta_only:
				obj.id = dataset_id
		return obj

	@classmethod
	def query_gene(cls, dataset_id, query_string, db):
		'''Given a query string for gene symbols, return matched
		gene symbols and their avg_expression.'''
		doc = db[cls.coll].find_one({'id': dataset_id}, 
			{'genes':True, 'avg_expression':True, '_id':False})
		genes_df = pd.DataFrame(doc)
		mask = genes_df.genes.str.contains(query_string, case=False)
		return genes_df.loc[mask].rename(columns={'genes': 'gene'})

	@classmethod
	def get_gene_expr(cls, dataset_id, gene, db):
		doc = db[cls.coll_expr].find_one({'dataset_id': dataset_id, 'gene': gene}, 
			{'values': True, '_id':False})
		return {gene: doc['values']}

	@classmethod
	def remove_all(cls, dataset_id, db):
		'''Remove all enrichment, visualization, dataset related to the dataset.'''
		db[cls.coll].delete_one({'id': dataset_id})
		db[cls.coll_expr].delete_many({'dataset_id': dataset_id})
		db['enrichr'].delete_many({'dataset_id': dataset_id})
		db['enrichr_temp'].delete_many({'dataset_id': dataset_id})
		db['vis'].delete_many({'dataset_id': dataset_id})


class GEODataset(GeneExpressionDataset):
	"""docstring for GEODataset"""
	def __init__(self, gse_id, organism='human', meta_doc=None, meta_only=False):
		self.id = gse_id
		self.organism = organism
		if not meta_only:
			# retrieve the expression matrix from the h5 file
			df, _ = self.retrieve_expression_and_meta(retrive_meta=False)
			if meta_doc is None:
				# df, meta_doc = self.retrieve_expression_and_meta(retrive_meta=True)
				meta_doc = self.retrieve_meta(df)
		else:
			df = pd.DataFrame(index=[], columns=meta_doc['meta_df']['geo_accession'])

		GeneExpressionDataset.__init__(self, df, meta=meta_doc)
		self.id = gse_id
		# self.meta = meta_doc
		# self.meta_df = pd.DataFrame(meta_doc['meta_df'])\
		# 	.set_index('Sample_geo_accession')
		


	def retrieve_expression_and_meta(self, retrive_meta=True):
		df, _ = load_read_counts_and_meta(organism=self.organism, gse=self.id,
			retrive_meta=False)
		# retrieve meta from GEO using the GSE class
		meta_doc = self.retrieve_meta(df)
		df = compute_CPMs(df)
		return df, meta_doc
	
	def save(self, db):
		if hasattr(self, 'd_sample_userListId'): 
			d_sample_userListId = self.d_sample_userListId
		else:
			d_sample_userListId = OrderedDict()

		doc = {
			'id': self.id,
			'organism': self.organism,
			'meta': self.meta,
			'sample_ids': self.sample_ids.tolist(),
			'genes': self.genes.tolist(),
			'avg_expression': self.avg_expression.tolist(),
			'd_sample_userListId': self.d_sample_userListId
		}
		insert_result = db[self.coll].insert_one(doc)
		gene_expression_docs = [
			{'dataset_id': self.id, 'gene':gene, 'values': values.tolist()} for gene, values in self.df.iterrows()
		]
		_ = db[self.coll_expr].insert(gene_expression_docs)
		return insert_result.inserted_id

	def retrieve_meta(self, df):
		'''Retrieve metadata from GEO through the GSE class'''
		gse = GSE(self.id)
		gse.retrieve()
		meta_df = gse.construct_sample_meta_df()
		# order/subset the samples
		meta_df = meta_df.loc[df.columns]
		meta_doc = gse.meta
		meta_doc['meta_df'] = meta_df.reset_index().to_dict(orient='list')
		return meta_doc

	def load_series_meta(self, db):
		'''Load series-level meta from `geo` collection.'''
		self.series = GSE.load(self.id, db).meta

	@classmethod
	def load(cls, gse_id, db, meta_only=False):
		'''Load from h5 file.'''
		projection = {'_id':False, 'meta':False} # not use the meta field in 'dataset' collection

		doc = db[cls.coll].find_one({'id': gse_id}, projection)

		gse = GSE.load(gse_id, db)
		meta_df = gse.construct_sample_meta_df()
		# order/subset the samples
		meta_df = meta_df.loc[doc['sample_ids']]
		meta_doc = gse.meta
		meta_doc['meta_df'] = meta_df.reset_index().to_dict(orient='list')

		obj = cls(doc['id'], organism=doc['organism'], meta_doc=meta_doc, meta_only=meta_only)
		return obj


