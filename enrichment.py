'''Utils for enrichment results
'''
import os, sys, json
from collections import OrderedDict
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def load_enrichment_from_library(gene_set_library):
	result_fn = os.path.join(SCRIPT_DIR, 'data/enrichr/', gene_set_library, 
		'combined_scores_df.csv')
	combined_scores_df = pd.read_csv(result_fn).set_index('Term')
	return combined_scores_df

def get_most_enriched_terms(combined_scores_df):
	non_missing_sample_mask = combined_scores_df.count() > 0
	max_idx = np.nanargmax(combined_scores_df.values[:, non_missing_sample_mask], 
		axis=0)
	top1_terms = np.empty(combined_scores_df.shape[1], dtype='object')
	top1_terms[~non_missing_sample_mask] = np.nan
	top1_terms[non_missing_sample_mask] = combined_scores_df.index[max_idx]
	return top1_terms

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
