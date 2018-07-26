import numpy as np

import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
pandas2ri.activate()

ro.r('''
	source('pseudotime_estimation.R')
''')

# from rpy2.robjects.packages import importr
# monocle = importr('monocle')

# makeCellData = ro.globalenv['makeCellData']
# runMonocleDDRTree = ro.globalenv['runMonocleDDRTree']
# convertToDataFrames = ro.globalenv['convertToDataFrames']

runMonoclePipeline = ro.globalenv['runMonoclePipeline']

def run_monocle_pipeline(df):
	'''Call the R function runMonoclePipeline then convert to results 
	to Python object.
	df: expression DataFrame indexed by genes
	'''
	rdf = pandas2ri.py2ri(df)
	res = runMonoclePipeline(rdf)
	parsed_res = {}
	for key in list(res.names):
		parsed_res[key] = pandas2ri.ri2py(res[res.names.index(key)])
	return parsed_res




## test 
# from database import *
# from pymongo import MongoClient

# MONGOURI='mongodb://146.203.54.131:27017/SCV'
# mongo = MongoClient(MONGOURI)

# db = mongo['SCV']

# from classes import *

# gse_id = 'GSE110499'
# print 'loading dataset %s' % gse_id
# gds = GEODataset.load(gse_id, db)
# print 'dataset shape: ', gds.df.shape

# rdf = pandas2ri.py2ri(gds.df)
# res = runMonoclePipeline(rdf)

# parsed_res = {}
# parsed_res['edge_df'] = pandas2ri.ri2py(res[res.names.index('edge_df')])
# parsed_res['data_df'] = pandas2ri.ri2py(res[res.names.index('data_df')])
