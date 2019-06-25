'''
This script subset the h5 files from ARCHS4 by GSE and platform, 
then upload to GCloud for notebook generator to retrieve.
'''
from __future__ import print_function
import os
import numpy as np
import pandas as pd
import h5py
from google.cloud import storage
import sys
# sys.path.append('../')
# from models.gene_expression import load_archs4_read_counts

client = storage.Client()
bucket = client.get_bucket('archs4-packages-v7')


# h5file = h5py.File('../data/human_matrix.h5', 'r')
h5file = h5py.File('../data/mouse_matrix.h5', 'r')

gses = h5file['meta']['Sample_series_id']
gsms = h5file['meta']['Sample_geo_accession']
platforms = h5file['meta']['Sample_platform_id']

meta_df = pd.DataFrame({
    'GSE': gses,
    'GSM': gsms,
    'platform': platforms,
    'Sample_characteristics_ch1': h5file['meta']['Sample_characteristics_ch1'],
    'Sample_title': h5file['meta']['Sample_title']
})
genes = h5file['meta']['genes']
genes = [g.encode('utf-8') for g in genes]

dt = h5py.special_dtype(vlen=str)

for (gse, platform), sub_df in meta_df.groupby(['GSE', 'platform']):
    if sub_df.shape[0] > 30 and 'Xx-xX' not in gse:

        h5_filename = '{gse}-{platform}.h5'.format(**locals())
        print(h5_filename)

        # remove from GCloud
        # blob = bucket.blob(h5_filename)
        # blob.delete()

        # write the h5 file
        h5out = h5py.File(h5_filename, 'w')

        # get expression 
        expression = h5file['data']['expression'][sub_df.index, :]
        expr_df = pd.DataFrame(expression, index=sub_df['GSM'], columns=genes)
        data = h5out.create_group('data')
        data.create_dataset('expression', data=expr_df)

        meta = h5out.create_group('meta')
        gene = meta.create_group('gene')
        gene.create_dataset('symbol', data=genes, dtype=dt)

        sample = meta.create_group('sample')
        sample.create_dataset('Sample_geo_accession', data=sub_df['GSM'].tolist(), dtype=dt)
        sample.create_dataset('Sample_title', data=sub_df['Sample_title'].tolist(), dtype=dt)


        # try to parse Sample_characteristics_ch1
        try:
            sample_characteristics = sub_df['Sample_characteristics_ch1']
            sample_characteristics_parsed = []

            for string in sample_characteristics:
                obj = {}
                for item in string.split('Xx-xX'):
                    key, val = item.split(': ')
                    obj[key] = val
                sample_characteristics_parsed.append(obj)
            
            sample_characteristics_parsed = pd.DataFrame(sample_characteristics_parsed)
        except Exception:
            pass
        else:
            for col in sample_characteristics_parsed:
                if sample_characteristics_parsed[col].nunique() > 1:
                    sample.create_dataset(col, data=sample_characteristics_parsed[col].tolist(), dtype=dt)
        

        h5out.close()

        blob = bucket.blob(h5_filename)
        blob.upload_from_filename(h5_filename, content_type='text/html')
        blob.make_public()

        # delete the file
        os.remove(h5_filename)


