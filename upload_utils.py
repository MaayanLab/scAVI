'''Utils handling uploaded datasets'''
import numpy as np
import pandas as pd

ALLOWED_EXTENSIONS = set(['txt', 'csv'])
def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_uploaded_files(data_file, metadata_file):
	if data_file.filename.endswith('.csv'):
		sep = ','
	elif data_file.filename.endswith('.txt'):
		sep = '\t'
	expr_df = pd.read_csv(data_file, sep=sep)
	expr_df.set_index(expr_df.columns[0], inplace=True)

	if metadata_file.filename.endswith('.csv'):
		sep = ','
	elif metadata_file.filename.endswith('.txt'):
		sep = '\t'
	meta_df = pd.read_csv(metadata_file, sep=sep)
	meta_df.set_index(meta_df.columns[0], inplace=True)

	meta_df = meta_df.loc[expr_df.columns]
	return expr_df, meta_df

def expression_is_valid(expr_df):
	if np.alltrue(expr_df.dtypes == np.int):
		return 'counts'
	elif np.alltrue(expr_df.dtypes == np.float):
		return 'normed_counts'
	else:
		raise ValueError('Some columns in the expression matrix are not numbers.')

