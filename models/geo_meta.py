'''Classes for interfacing with metadata on GEO
'''
import os
import warnings
from rpy2.rinterface import RRuntimeError

with warnings.catch_warnings():
	warnings.simplefilter("ignore")
	try:
		import geo_query as gq
	except (ImportError, RRuntimeError) as e:
		pass

import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))



class GSE(object):
	"""docstring for GSE"""
	coll = 'geo'
	id_field = 'geo_accession'
	def __init__(self, geo_id):
		self.id = geo_id
		self.meta = {}
		self.GSMs = _GSMList(self.id)

	def retrieve(self):
		'''Retrieve metadata of GSE and GSMs from GEO'''
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")
			gse_obj = gq.download_gse(self.id)
			gse_meta = gq.retrieve_gse_meta(gse_obj)
			gse_meta = gq.convert_r_list(gse_meta)
			# make sure the id_field exist
			gse_meta[self.id_field] = self.id
			self.meta = gse_meta
			self.GSMs.retrieve(gse_obj, gse_meta)

	def construct_sample_meta_df(self):
		'''Construct a dataframe for metadata based on GSMs'''
		meta_df = self.GSMs.construct_sample_meta_df()
		meta_df = meta_df.loc[self.meta['sample_id']]
		return meta_df

	def save(self, db):
		'''Save to database'''
		insert_result = db[self.coll].insert_one(self.meta)
		self.GSMs.save(db)
		return insert_result.inserted_id

	@classmethod
	def load(cls, geo_id, db):
		'''Load from the database.'''
		doc = db[cls.coll].find_one({cls.id_field: geo_id}, {'_id':False})
		obj = cls(geo_id)
		obj.meta = doc
		obj.GSMs = _GSMList.load(obj, db)
		return obj


def unpack_gse_meta(d):
	parsed_d = {}
	for key, value in d.items():
		if type(value) == list:
			for val in value:
				if val.count(': ') == 1:
					k, v = val.split(': ')
					parsed_d[k] = v
		else:
			parsed_d[key] = value
	return parsed_d


class _GSMList(object):
	"""docstring for _GSMList, this class will only be used internally for GSE"""
	coll = 'gsm'
	id_field = 'geo_accession'
	def __init__(self, gse_id):
		self.gse_id = gse_id
		self.GSMs = []
	
	def retrieve(self, gse_obj, gse_meta):
		'''Retrieve GSM metas from gse_obj'''
		gsm_metas = gq.retrieve_gsms_meta_from_gse(gse_obj)
		gsm_metas = gq.convert_gsms_meta_r_list(gsm_metas)
		gsm_metas = gq.drop_duplicated_meta_in_gsm(gse_meta, gsm_metas)

		for gsm_id, gsm_meta in gsm_metas.items(): 
			gsm_meta[self.id_field] = gsm_id
			self.GSMs.append(gsm_meta)

	def __len__(self):
		return len(self.GSMs)

	def construct_sample_meta_df(self):
		''''''
		# unpack GSM meta fields that are lists
		meta_df = pd.DataFrame.from_records(map(unpack_gse_meta, self.GSMs))\
			.set_index(self.id_field)
		# remove columns with only 1 unique value
		meta_df = meta_df.loc[:, meta_df.nunique() > 1]
		# replace column names with '.' 
		meta_df.columns = meta_df.columns.map(lambda x:x.replace('.', '_'))
		# attempt to convert columns to numerical type
		meta_df.replace('NA', np.nan, inplace=True)
		for col in meta_df.columns:
			meta_df[col] = pd.to_numeric(meta_df[col], errors='ignore')
		return meta_df

	def save(self, db):
		'''Save to database'''
		insert_result = db[self.coll].insert_many(self.GSMs)
		return insert_result.inserted_ids

	@classmethod
	def load(cls, gse, db):
		'''Load from the database. Need a GSE instance as param.'''
		cur = db[cls.coll].find({cls.id_field: {'$in': gse.meta['sample_id']}}, {'_id': False})
		obj = cls(gse.id)
		obj.GSMs = [doc for doc in cur]

		return obj
