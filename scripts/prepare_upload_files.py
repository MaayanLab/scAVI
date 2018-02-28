'''
Prepare some files to test the upload functionality.
'''
import sys
sys.path.append('../')
from database import *
from pymongo import MongoClient
mongo = MongoClient(MONGOURI)

db = mongo['SCV']
coll = db['dataset']

from gene_expression import *


expr_df, meta_doc = load_read_counts_and_meta(organism='mouse', gse='GSE96870')

# rename the samples
expr_df.columns = ['sample_%d' % i for i in range(len(expr_df.columns))]


meta_df = pd.DataFrame(meta_doc['meta_df'])
meta_df.index = expr_df.columns
meta_df.index.name = 'sample_ID'

# parse the meta_df a bit
meta_df['Sample_characteristics_ch1'] = meta_df['Sample_characteristics_ch1'].map(lambda x:x.split('\t'))
keys_from_char_ch1 = [item.split(': ')[0] for item in meta_df['Sample_characteristics_ch1'][0]]

for i, key in enumerate(keys_from_char_ch1):
	meta_df[key] = meta_df['Sample_characteristics_ch1'].map(lambda x:x[i].split(': ')[1])
# drop unnecessary columns in meta_df
meta_df = meta_df.drop(['Sample_characteristics_ch1', 
	'Sample_relation', 'Sample_geo_accession', 'Sample_supplementary_file_1'],
	axis=1)
# fake a column of continuous values
meta_df['random_continuous_attr'] = np.random.randn(meta_df.shape[0])

meta_df.to_csv('../data/sample_metadata.csv')

# raw read counts
expr_df.to_csv('../data/sample_read_counts_%dx%d.csv' % expr_df.shape)

# CPMs 
expr_df = compute_CPMs(expr_df)
expr_df.to_csv('../data/sample_CPMs_%dx%d.csv' % expr_df.shape)
