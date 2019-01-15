'''
This script uses the notebook-generator-server-sc to produce notebook for all 
public GSE data in SCAVI and adds the notebook_uid into the MongoDB.
'''
from __future__ import print_function
import os
import json
import requests

from pymongo import MongoClient
import pandas as pd

mongo = MongoClient(os.environ['MONGOURI'])
db = mongo['SCV']

endpoint = 'http://amp.pharm.mssm.edu/notebook-generator-server-sc/api/generate'
notebook_configuration_base = {
  "notebook": {
    "title": "",
    "live": "False",
    "version": "v1.0.5"
  },
  "tools": [
    {
      "tool_string": "pca",
      "parameters": {
        "nr_genes": "500",
        "normalization": "CPM",
        "z_score": "True",
        "plot_type": "interactive"
      }
    },
    {
        "tool_string": "pca",
        "parameters": {
          "nr_genes": "500",
          "normalization": "magic",
          "z_score": "True",
          "plot_type": "interactive"
        }
     },     
    {
      "tool_string": "clustering",
      "parameters": {
        "nr_genes": "500",
        "normalization": "logCPM",
        "plot_type": "interactive"
      }
    },
    {
      "tool_string": "monocle",
      "parameters": {
        "color_by": "Pseudotime",
        "plot_type": "interactive"
      }
    },
    {
      "tool_string": "library_size_analysis",
      "parameters": {
        "plot_type": "interactive"
      }
    }
  ],
  "data": {
    "source": "archs4",
    "parameters": {
      "gse": "",
      "platform": ""
    }
  },
  "signature": {},
  "terms": []
}

# find existing GEO datasets in the DB
cur = db['dataset'].find(
	{'$and': [
		{'id': {'$regex': r'^GSE'}},
		{'sample_ids.30': {'$exists': True}},
        {'notebook_uid': {'$exists': False}}
	]}, projection={'id':True, 'meta': True})
    
gse_df = [] 
for doc in cur:
    if 'platform_id' in doc['meta']:
        gpl = doc['meta'].get('platform_id')
    else:
        gpl = doc['meta'].get('Sample_platform_id')
    rec = {'gse': doc['id'], 'gpl': gpl}
    gse_df.append(rec)

print('N GSEs: ', len(gse_df))
gse_df = pd.DataFrame(gse_df)

c = 0
for _, row in gse_df.dropna().iterrows():
    gse_id = row['gse']
    gpl_id = row['gpl']
    if type(gpl_id) != list:
        notebook_configuration = notebook_configuration_base.copy()

        notebook_configuration['notebook']['title'] = '%s Analysis Notebook' % gse_id
        notebook_configuration['data']['parameters']['gse'] = gse_id
        notebook_configuration['data']['parameters']['platform'] = gpl_id

        try:
            response =  requests.post(endpoint, json=notebook_configuration)
            notebook_uid = response.json()['notebook_uid']
        except Exception as e:
            print(e)
            pass
        else:
            db['dataset'].update_one({'id': gse_id}, {'$set': {'notebook_uid': notebook_uid}})
            c += 1
            print('Notebook completed: ', response.json()['nbviewer_url'])
            if c % 5 == 0:
                print('%d/%d completed' % (c, gse_df.shape[0]))
