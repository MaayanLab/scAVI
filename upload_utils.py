'''Utils handling uploaded datasets'''
import os
import time
import numpy as np
import pandas as pd
from bson.objectid import ObjectId

ALLOWED_EXTENSIONS = set(['txt', 'tsv', 'csv'])
def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def expression_is_valid(expr_df):
	if np.alltrue(expr_df.dtypes == np.int):
		return 'counts'
	elif np.alltrue(expr_df.dtypes == np.float):
		return 'normed_counts'
	else:
		raise ValueError('Some columns in the expression matrix are not numbers.')


class Upload(object):
	"""Class for tracking uploaded files."""
	coll = 'upload'
	# class variables that should be set in application context:
	upload_folder = None
	db = None 
	def __init__(self, data_file, metadata_file=None, save=True):
		self.data_file = data_file
		self.metadata_file = metadata_file
		if save:
			self.started = False
			self.done = False
			self.id = self.save()
	
	def save(self):
		doc = {
			'data_file': self.data_file,
			'metadata_file': self.metadata_file,
			'started': self.started,
			'done': self.done
		}
		insert_result = self.db[self.coll].insert_one(doc)
		return str(insert_result.inserted_id)

	def get_time_stamp(self):
		oid = ObjectId(self.id)
		return oid.generation_time

	def start(self):
		# Set the started flag to True and update the doc in db
		self.started = True,
		self.db[self.coll].update_one({'_id': ObjectId(self.id)},
			{'$set': {'started': True}})

	def finish(self, dataset_id):
		# Set the done flag to True and update the doc in db
		self.done = True
		self.dataset_id = dataset_id
		self.db[self.coll].update_one({'_id': ObjectId(self.id)},
			{'$set': {'done': True, 'dataset_id': dataset_id}})

	def parse(self):
		# Parse the files into pd.DataFrame
		if self.data_file.endswith('.csv'):
			sep = ','
		elif self.data_file.endswith('.txt') or self.data_file.endswith('.tsv'):
			sep = '\t'
		expr_df = pd.read_csv(os.path.join(self.upload_folder, self.data_file), sep=sep)
		expr_df.set_index(expr_df.columns[0], inplace=True)
		
		if self.metadata_file.endswith('.csv'):
			sep = ','
		elif self.metadata_file.endswith('.txt') or self.metadata_file.endswith('.tsv'):
			sep = '\t'
		meta_df = pd.read_csv(os.path.join(self.upload_folder, self.metadata_file), sep=sep)
		meta_df.set_index(meta_df.columns[0], inplace=True)

		meta_df = meta_df.loc[expr_df.columns]
		return expr_df, meta_df

	@classmethod
	def exists(cls, upload_id):
		doc = cls.db[cls.coll].find_one({'_id': ObjectId(upload_id)})
		return doc is not None

	@classmethod
	def load(cls, upload_id):
		doc = cls.db[cls.coll].find_one({'_id': ObjectId(upload_id)})
		obj = cls(doc['data_file'], doc['metadata_file'], save=False)
		obj.id = upload_id
		obj.started = doc['started']
		obj.done = doc['done']
		obj.dataset_id = doc.get('dataset_id', None)
		return obj
