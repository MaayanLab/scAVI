'''Utils for gene expression
'''
import os, sys
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def load_read_counts():
	fn = os.path.join(SCRIPT_DIR, 'data/Transcriptome Data.csv')
	expr_df = pd.read_csv(fn, sep='\t')
	expr_df.index = expr_df.index.map(lambda x:x.split('__')[0])
	return expr_df

def load_CPM_matrix(CPM_cutoff=0.3, at_least_in_n_samples=10):
	meta_df = pd.read_excel(os.path.join(SCRIPT_DIR, 'data/Index Sort Matrix_04_MR.xlsx'), 
		sheetname='Sheet1')
	meta_df = meta_df.set_index('Well')	
	exp_wells = meta_df.columns[2:]

	expr_df = load_read_counts()
	# Compute CPM for expression levels
	CPM_df = (expr_df * 1e9) / expr_df.sum(axis=0)

	# and remove spike-in samples
	CPM_df = CPM_df.loc[:, exp_wells]
	## Filter out non-expressed genes
	CPM_df = CPM_df.loc[CPM_df.sum(axis=1) > 0, :]
	## Filter out lowly expressed genes
	mask_low_vals = (CPM_df > CPM_cutoff).sum(axis=1) > at_least_in_n_samples
	CPM_df = CPM_df.loc[mask_low_vals, :]
	
	return CPM_df


