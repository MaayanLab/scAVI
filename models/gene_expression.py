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

from .geo_meta import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def load_read_counts(organism='human', gsms=[]):
	'''Load data from h5 file using a list of GSMs.
	'''
	fn = os.path.abspath(os.path.join(SCRIPT_DIR, '../data/%s_matrix.h5' % organism))
	f = h5py.File(fn, 'r')
	mat = f['data']['expression']

	all_gsms = f['meta']['Sample_geo_accession']
	sample_mask = np.in1d(all_gsms, gsms)
	if sample_mask.sum() == 0:
		raise RuntimeError('None of the gsms %s exists in the h5 file %s_matrix.h5' % 
			(gsms, organism))
	else:
		sample_ids = all_gsms[sample_mask]
		genes = f['meta']['genes']
		# to prevent MongoDB error
		genes = map(lambda x:x.replace('.', '_'), genes)		
		# Retrieve gene by sample matrix
		expr_df = pd.DataFrame(mat[sample_mask, :].T, index=genes, columns=sample_ids)

		# Filter out non-expressed genes
		expr_df = expr_df.loc[expr_df.sum(axis=1) > 0, :] 

		# Filter out samples with very low read counts
		# valid_sample_mask = expr_df.sum(axis=0) > 100
		# expr_df = expr_df.loc[:, valid_sample_mask]

		return expr_df


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
		self.sample_ids = df.columns.tolist()
		self.genes = df.index
		self.enrichment_results = enrichment_results
		self.visualizations = visualizations
		self.meta = meta
		self.meta_df = pd.DataFrame(meta.get('meta_df', {}), index=self.sample_ids)
		self.id = hashlib.md5(self.df.values.tobytes()).hexdigest()
	
	def log10_and_zscore(self):
		self.df = log10_and_zscore(self.df)

	def is_zscored(self):
		return self.df.min().min() < 0

	def DEGs_posted(self, db, etype='genewise-z'):
		'''Whether DEGs (from etype) has been POSTed to Enrichr.'''
		result = False
		if hasattr(self, 'd_sample_userListId'):
			if etype in self.d_sample_userListId:
				result = True
		else:
			doc = db[self.coll].find_one({'id': self.id}, 
				{'d_sample_userListId':True, '_id':False})
			if doc:
				if len(doc.get('d_sample_userListId', {})) > 0:
					d_sample_userListId = doc['d_sample_userListId'].get(etype, {})
					if len(d_sample_userListId) > 0 and None not in d_sample_userListId.values():
						# make sure the userListIds does not contain None
						result = True
		return result

	def identify_DEGs_genewise_z(self, cutoff=2.33):
		if not self.is_zscored():
			self.log10_and_zscore()
		up_DEGs_df = self.df > cutoff
		return up_DEGs_df

	def identify_DEGs_samplewise_z(self, cutoff=2.33):
		assert not self.is_zscored()
		zscore_df = self.df.apply(lambda x: (x-x.mean())/x.std(ddof=0), axis=0)
		up_DEGs_df = zscore_df > cutoff
		return up_DEGs_df

	def identify_DEGs_from_background(self, cutoff=2.33, genes_meta=None):
		assert not self.is_zscored()
		df = self.df.copy()
		# Filter out genes not in genes_meta
		df = df.loc[df.index.isin(genes_meta.index)]
		genes, samples = df.index, df.columns
		gene_means = genes_meta.loc[df.index, 'mean_cpm'].values
		gene_stds = genes_meta.loc[df.index, 'std_cpm'].values
		# Compute gene-wise z-scores
		df = (df.values - gene_means.reshape(-1, 1)) / gene_stds.reshape(-1, 1)
		up_DEGs_mat = df > cutoff
		up_DEGs_df = pd.DataFrame(up_DEGs_mat, index=genes, columns=samples)
		return up_DEGs_df

	def identify_DEGs(self, cutoff=2.33, etype='genewise-z', genes_meta=None):
		if etype == 'genewise-z':
			up_DEGs_df = self.identify_DEGs_genewise_z(cutoff)
		elif etype == 'samplewise-z':
			up_DEGs_df = self.identify_DEGs_samplewise_z(cutoff)
		else:
			up_DEGs_df = self.identify_DEGs_from_background(cutoff, genes_meta)
		return up_DEGs_df

	def post_DEGs_to_Enrichr(self, db, cutoff=2.33, etype='genewise-z', genes_meta=None):
		if not self.DEGs_posted(db, etype):
			up_DEGs_df = self.identify_DEGs(cutoff, etype, genes_meta)
			d_sample_userListId = OrderedDict()

			for sample_id in self.sample_ids:
				up_genes = self.genes[np.where(up_DEGs_df[sample_id])[0]].tolist()
				user_list_id = None
				if len(up_genes) > 10:
					user_list_id = post_genes_to_enrichr(up_genes, '%s up' % sample_id)

				d_sample_userListId[sample_id] = user_list_id
			# nest
			d_sample_userListId = {etype: d_sample_userListId}
		else:
			doc = db.get_collection(self.coll, codec_options=CodecOptions(OrderedDict))\
				.find_one({'id': self.id},
					{'d_sample_userListId.%s'%etype:True, '_id':False},
					)
			d_sample_userListId = doc['d_sample_userListId']

		self.d_sample_userListId = d_sample_userListId
		return d_sample_userListId

	def save_DEGs(self, db, etype='genewise-z'):
		# Save d_sample_userListId to the existing doc in the db
		if hasattr(self, 'd_sample_userListId'): 
			d_sample_userListId = self.d_sample_userListId
			db[self.coll].update({'id': self.id}, {'$set': 
				{'d_sample_userListId.%s'% etype: d_sample_userListId[etype]}})


	def save(self, db):
		if hasattr(self, 'd_sample_userListId'): 
			d_sample_userListId = self.d_sample_userListId
		else:
			d_sample_userListId = OrderedDict()
		doc = {
			'id': self.id,
			'meta': self.meta,
			'sample_ids': self.sample_ids,
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

	def start(self, db):
		# Set the started flag to True and update the doc in db
		self.started = True,
		db[self.coll].update_one({'id': self.id},
			{'$set': {'started': True}})

	def finish(self, db):
		# Set the done flag to True and update the doc in db
		self.done = True
		db[self.coll].update_one({'id': self.id},
			{'$set': {'done': True}})

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
			obj.id = dataset_id
			obj.started = doc.get('started', False)
			obj.done = doc.get('done', False)
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
	def __init__(self, gse_id, organism='human', meta_doc=None, meta_only=False, expression_kwargs={}):
		self.id = gse_id
		self.organism = organism
		if meta_doc is None:
			# retrieve meta from GEO using the GSE class
			meta_doc = self.retrieve_meta()

		self.sample_ids = meta_doc['sample_id']
		if not meta_only:
			# retrieve the expression matrix from the h5 file
			df = self.retrieve_expression(expression_kwargs=expression_kwargs)
		else:
			df = pd.DataFrame(index=[], columns=self.sample_ids)

		# order/subset the samples
		meta_df = pd.DataFrame(meta_doc['meta_df'], index=self.sample_ids)
		meta_df = meta_df.loc[df.columns]
		self.sample_ids = df.columns.tolist()
		meta_df = meta_df.loc[:, meta_df.nunique() > 1]
		# update meta_doc
		meta_doc['meta_df'] = meta_df.to_dict(orient='list')
		meta_doc['sample_id'] = self.sample_ids

		GeneExpressionDataset.__init__(self, df, meta=meta_doc)
		self.id = gse_id		
		# self.meta = meta_doc
		# self.meta_df = pd.DataFrame(meta_doc['meta_df'])\
		# 	.set_index('Sample_geo_accession')
		

	def retrieve_expression(self, expression_kwargs={}):
		'''Retrieve gene expression from the h5 file'''
		df= load_read_counts(organism=self.organism, gsms=self.sample_ids)
		df = compute_CPMs(df, **expression_kwargs)
		return df
	
	def save(self, db):
		if hasattr(self, 'd_sample_userListId'): 
			d_sample_userListId = self.d_sample_userListId
		else:
			d_sample_userListId = OrderedDict()

		doc = {
			'id': self.id,
			'organism': self.organism,
			'meta': self.meta,
			'sample_ids': self.sample_ids,
			'genes': self.genes.tolist(),
			'avg_expression': self.avg_expression.tolist(),
			'd_sample_userListId': self.d_sample_userListId
		}
		insert_result = db[self.coll].insert_one(doc)
		gene_expression_docs = [
			{'dataset_id': self.id, 'gene':gene, 'values': values.tolist()} for gene, values in self.df.iterrows()
		]
		_ = db[self.coll_expr].insert(gene_expression_docs)

		if hasattr(self, 'gse'):
			self.gse.save(db)
		return insert_result.inserted_id

	def retrieve_meta(self):
		'''Retrieve metadata from GEO through the GSE class'''
		gse = GSE(self.id)
		gse.retrieve()
		meta_df = gse.construct_sample_meta_df()
		self.gse = gse
		# # order/subset the samples
		# meta_df = meta_df.loc[df.columns]
		# meta_df = meta_df.loc[:, meta_df.nunique() > 1]
		meta_doc = gse.meta
		meta_doc['meta_df'] = meta_df.to_dict(orient='list')
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
		meta_df = meta_df.loc[:, meta_df.nunique() > 1]
		meta_doc = gse.meta
		meta_doc['meta_df'] = meta_df.to_dict(orient='list')
		meta_doc['sample_id'] = meta_df.index.tolist()

		obj = cls(doc['id'], organism=doc['organism'], meta_doc=meta_doc, meta_only=meta_only)
		return obj


