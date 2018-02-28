'''Utils for enrichment results
'''
import os, sys, json
import requests
from collections import OrderedDict
import numpy as np
import pandas as pd

from utils import nan_to_none
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def get_most_enriched_terms(combined_scores_df):
	non_missing_sample_mask = combined_scores_df.count() > 0
	max_idx = np.nanargmax(combined_scores_df.values[:, non_missing_sample_mask], 
		axis=0)
	top1_terms = np.empty(combined_scores_df.shape[1], dtype='object')
	top1_terms[~non_missing_sample_mask] = np.nan
	top1_terms[non_missing_sample_mask] = combined_scores_df.index[max_idx]
	return top1_terms.tolist()

def load_all_enrichment_results():
	'''Read enrichr folder to load all available enrichment results.
	'''
	d_lib_combined_score_df = OrderedDict()
	d_lib_top_terms = OrderedDict()
	

	gene_set_libraries = os.walk(os.path.join(SCRIPT_DIR, 'data/enrichr/')).next()[1]
	libraries = []
	terms = []
	for gene_set_library in gene_set_libraries:
		combined_scores_df = load_enrichment_from_library(gene_set_library)
		top1_terms = get_most_enriched_terms(combined_scores_df)

		d_lib_combined_score_df[gene_set_library] = combined_scores_df
		d_lib_top_terms[gene_set_library] = top1_terms.tolist()

		libraries.extend([gene_set_library] * combined_scores_df.shape[0])
		terms.extend(combined_scores_df.index.tolist())	

	all_terms_df = pd.DataFrame({'library': libraries, 'term': terms})
	return d_lib_combined_score_df, d_lib_top_terms, all_terms_df


def get_enrichment(user_list_id, gene_set_library):
	ENRICHR_URL = 'http://amp.pharm.mssm.edu/Enrichr/enrich'
	query_string = '?userListId=%s&backgroundType=%s'
	response = requests.get(
		ENRICHR_URL + query_string % (user_list_id, gene_set_library)
		)
	if not response.ok:
		print 'Error fetching enrichment results for list: %s' % user_list_id
		raise Exception('Error fetching enrichment results.')

	data = json.loads(response.text)
	return data


def find_library_for_term(term, db):
	doc = db['enrichr'].find_one({'terms': term}, {'_id':False, 'gene_set_library':True})
	return doc['gene_set_library']

class EnrichmentResults(object):
	"""EnrichmentResults of a list of DEGs on a single gene_set_library"""
	coll = 'enrichr'
	colnames = ['Rank', 'Term', 'P-value', 'Z-score', 'Combined score', 
		'Overlapping genes', 'Adjusted p-value', 
		'Old p-value', 'Old adjusted p-value']

	def __init__(self, ged=None, gene_set_library=None):
		self.ged = ged # GeneExpressionDataset instance
		self.gene_set_library = gene_set_library

	def do_enrichment(self, db):
		ged = self.ged
		for sample_id, user_list_id in ged.d_sample_userListId.items():
			if user_list_id:
				res = get_enrichment(user_list_id, self.gene_set_library)
				res['sample_id'] = sample_id
				res['gene_set_library'] = self.gene_set_library
				res['dataset_id'] = self.ged.id
				db['enrichr_temp'].insert_one(res)

	def summarize(self, db):
		'''
		Get top enriched term based on combined score.
		Also get the top enriched terms for samples.
		'''
		combined_scores_df = None
		for sample_id in self.ged.sample_ids:
			doc = db['enrichr_temp'].find_one({
				'sample_id': sample_id,
				'gene_set_library': self.gene_set_library
				})
			if doc:
				df = pd.DataFrame(doc[self.gene_set_library],
					columns=self.colnames)\
					[['Term', 'Combined score']]\
					.set_index('Term')\
					.rename(index=str, columns={'Combined score': sample_id})
			else:
				df = None
			if combined_scores_df is None:
				combined_scores_df = df
			else:
				if df is None:
					combined_scores_df[sample_id] = np.nan
				else:
					combined_scores_df = combined_scores_df.merge(df, 
						left_index=True,
						right_index=True,
						how='outer')
		self.combined_scores_df = combined_scores_df
		self.top1_terms = get_most_enriched_terms(combined_scores_df)
		return combined_scores_df

	def save(self, db):
		scores = self.combined_scores_df.transpose().to_dict('list')
		doc = {
			'scores': scores,
			'sample_ids': self.combined_scores_df.columns.tolist(),
			'terms': self.combined_scores_df.index.tolist(),
			'gene_set_library': self.gene_set_library,
			'dataset_id': self.ged.id,
			'top1_terms': self.top1_terms
		}
		insert_result = db[self.coll].insert_one(doc)
		return insert_result.inserted_id

	def remove_intermediates(self, db):
		db['enrichr_temp'].remove({'$and': [
				{'sample_id': {'$in': self.ged.sample_ids.tolist()}},
				{'gene_set_library': self.gene_set_library}
			]})
		return

	@classmethod
	def load(cls, dataset_id, gene_set_library, db):
		'''Load from DB'''

		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'gene_set_library': gene_set_library}
			]})
		obj = cls(ged=None, gene_set_library=gene_set_library)
		obj.combined_scores_df = pd.DataFrame(doc['scores'], index=doc['sample_ids'])
		obj.top1_terms = doc['top1_terms']
		return obj

	@classmethod
	def get_term_scores(cls, dataset_id, gene_set_library, term, db):
		'''Given dataset_id, gene_set_library, term, find the scores of the samples.
		'''
		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'gene_set_library': gene_set_library}
			]}, 
			{'scores.%s'%term:True, '_id': False}
			)
		doc['scores'][term] = map(nan_to_none, doc['scores'][term])
		return doc['scores']

	@classmethod
	def get_top_terms(cls, dataset_id, gene_set_library, db):
		'''Return the list top enriched terms for samples.
		'''
		doc = db[cls.coll].find_one({'$and': [
				{'dataset_id': dataset_id},
				{'gene_set_library': gene_set_library}
			]}, 
			{'top1_terms':True, '_id':False}
			)
		return {gene_set_library: map(nan_to_none, doc['top1_terms'])}
