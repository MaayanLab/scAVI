'''
Search the NCBI GEO database to find single-cell RNA-seq studies.
'''
from __future__ import division
import math
import json
import time
from datetime import datetime

import pandas as pd
from Bio import Entrez
Entrez.email = "zichen.wang@mssm.edu"

term = '''
("expression profiling by high throughput sequencing"[DataSet Type]) AND \
    (("single cell"[Description]) OR ("single-cell"[Description])) AND \
    (("homo sapiens"[Organism]) OR ("mus musculus"[Organism]))
'''
n_samples_cutoff = 50

now = datetime.now()
timestamp = now.strftime('%Y-%m-%d')

# Search for studies
handle = Entrez.esearch(db="gds", 
                        term=term,
                        usehistory="y"
                       )
search_result = Entrez.read(handle)
n_total = int(search_result['Count'])
print '# single-cell RNA-seq studies found: ', n_total

# Get GSEs
batch_size = 10
n_batches = int(math.ceil(n_total / batch_size))
print n_batches
gse_meta_df = pd.DataFrame(columns=['GSE', 'n_samples', 'organism', 'title'])

c = 0
for i in range(n_batches):
    time.sleep(1)
    retstart = (i*batch_size)+1
    try:
        handle = Entrez.esummary(db='gds', 
                                rettype='summary',
                                retmode='json',
                                retstart=retstart,
                                retmax=batch_size,
                                webenv=search_result['WebEnv'],
                                query_key=search_result['QueryKey']
                                )
    except Exception as e:
        print e
        pass
    else:
        results = json.loads(handle.read())
        for key, rec in results['result'].items():
            if key != 'uids':
                gse = 'GSE%s' % rec['gse']
                if rec['taxon'] == 'Mus musculus':
                    organism = 'mouse'
                elif rec['taxon'] == 'Homo sapiens':
                    organism = 'human'
                gse_meta_df.loc[c] = (gse, rec['n_samples'], organism, rec['title'])
                c += 1
        print 'Batch-%d GSEs retrieved: %d' % (i, gse_meta_df.shape[0])

print 'GSEs retrieved: ', gse_meta_df.shape[0]

def cast_int(x):
    try:
        x = int(x)
    except ValueError:
        x = 0
    return x

gse_meta_df.n_samples = gse_meta_df.n_samples.map(cast_int)
gse_meta_df = gse_meta_df.set_index('GSE')

# Filter out low samples GSEs
gse_meta_df = gse_meta_df.query('n_samples > %d' % n_samples_cutoff).sort_values('n_samples')
print 'GSEs after filtering: ', gse_meta_df.shape[0]

gse_meta_df.to_csv('scRNAseq_GSEs-%s.csv' % timestamp, encoding='utf-8')
