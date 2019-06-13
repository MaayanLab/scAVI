import os, sys
import math
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy import io

h5_file = h5py.File('filtered_gene_bc_matrices_h5.h5', 'r')
group_name = h5_file.keys()[0]
group = h5_file[group_name]
# barcodes <class 'h5py._hl.dataset.Dataset'>
# data <class 'h5py._hl.dataset.Dataset'>
# gene_names <class 'h5py._hl.dataset.Dataset'>
# genes <class 'h5py._hl.dataset.Dataset'>
# indices <class 'h5py._hl.dataset.Dataset'>
# indptr <class 'h5py._hl.dataset.Dataset'>
# shape <class 'h5py._hl.dataset.Dataset'>

mat = group['data']

gene_ids = group['genes'][:]
genes = group['gene_names'][:]
barcodes = group['barcodes'][:]
n_genes, n_samples = len(genes), len(barcodes)

# Construct a sparse matrix object
mat = sp.csr_matrix((group['data'], group['indices'], group['indptr']),
	shape=(n_samples, n_genes))

sample_idx = np.random.choice(mat.shape[0], 100, replace=False)
mat_sub = mat[sample_idx]
mat_sub = mat_sub[:, np.random.permutation(np.arange(n_genes))]

barcodes_sub = barcodes[sample_idx]
barcodes_sub_mod = map(lambda x: ''.join(np.random.choice(list('ATGC'), 3, replace=True))+x, 
	barcodes_sub)
barcodes_sub_mod = np.array(barcodes_sub_mod)

h5_example_file = h5py.File('example_read_count_matrix.h5', 'w')
grp = h5_example_file.create_group('hg19')

grp.create_dataset('barcodes', data=barcodes_sub_mod)
grp.create_dataset('gene_names', data=genes)
grp.create_dataset('genes', data=gene_ids)

grp.create_dataset('data', data=mat_sub.data)
grp.create_dataset('indices', data=mat_sub.indices)
grp.create_dataset('indptr', data=mat_sub.indptr)
grp.create_dataset('shape', data=np.array([mat_sub.shape[1], mat_sub.shape[0]]).astype(np.int32))
h5_example_file.close()
h5_file.close()


# Create sample file in mtx format
mat = io.mmread('matrix.mtx')
# In [16]: type(mat)
# Out[16]: scipy.sparse.coo.coo_matrix
genes = pd.read_csv('genes.tsv', sep='\t', names=['gene_ids', 'gene_symbols'])
barcodes = pd.read_csv('barcodes.tsv', sep='\t', names=['barcodes'])['barcodes']

sample_idx = np.random.choice(mat.shape[1], 100, replace=False)
mat_sub = mat.tocsr()[:, sample_idx]
mat_sub = mat_sub.tocoo()
barcodes_sub = barcodes.loc[sample_idx]
barcodes_sub.to_csv('example_barcodes.tsv', index=False, header=False)
genes.to_csv('example_genes.tsv', index=False, header=False, sep='\t')

io.mmwrite('example_matrix', mat_sub)
