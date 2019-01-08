'''Utils handling uploaded datasets'''
import os
import time
import h5py
import numpy as np
import pandas as pd
from bson.objectid import ObjectId
from google.cloud import storage

from models.gene_expression import parse_10x_h5, parse_10x_mtx

ALLOWED_EXTENSIONS = set(['txt', 'tsv', 'csv', 'h5', 'mtx'])
def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def expression_is_valid(expr_df):
	if np.alltrue([np.issubdtype(x, np.integer) for x in expr_df.dtypes]):
		return 'counts'
	elif np.alltrue([np.issubdtype(x, np.float) for x in expr_df.dtypes]):
		return 'normed_counts'
	else:
		raise ValueError('Some columns in the expression matrix are not numbers.')

def get_exception_message(e):
	msg = '%s: %s.' % (type(e).__name__, str(e))
	return msg


class Upload(object):
	"""Class for tracking uploaded files."""
	coll = 'upload'
	# class variables that should be set in application context:
	upload_folder = None
	db = None 
	
	def __init__(self, files={}, save=True, type_=None):
		self.files = files
		self.type_ = type_
		if save:
			self.started = False
			self.done = False
			self.error = False
			self.id = self.save()
	
	def save(self):
		doc = {
			'files': self.files,
			'started': self.started,
			'done': self.done,
			'error': self.error,
			'type': self.type_
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

	def catch_error(self, e):
		self.error = True
		self.db[self.coll].update_one({'_id': ObjectId(self.id)},
			{'$set': {'error': True, 'e': get_exception_message(e)}})

	def parse(self):
		# Parse the files into pd.DataFrame(s): expr_df and meta_df
		files = self.files
		upload_folder = self.upload_folder
		if self.type_ == 'plain_text':
			if files['data_file'].endswith('.csv'):
				sep = ','
			elif files['data_file'].endswith('.txt') or files['data_file'].endswith('.tsv'):
				sep = '\t'
			expr_df = pd.read_csv(os.path.join(upload_folder, files['data_file']), sep=sep)
			expr_df.set_index(expr_df.columns[0], inplace=True)
			
			if files['metadata_file'].endswith('.csv'):
				sep = ','
			elif files['metadata_file'].endswith('.txt') or files['metadata_file'].endswith('.tsv'):
				sep = '\t'
			meta_df = pd.read_csv(os.path.join(upload_folder, files['metadata_file']), sep=sep)
			meta_df.set_index(meta_df.columns[0], inplace=True)
			meta_df = meta_df.loc[expr_df.columns]
			
		elif self.type_ == '10x_h5': # h5 file from 10x Genomics
			expr_df, meta_df = parse_10x_h5(os.path.join(upload_folder, files['h5_file']))
		elif self.type_ == '10x_mtx': 
			# mtx file and metadata files from 10x Genomics
			expr_df, meta_df = parse_10x_mtx(os.path.join(upload_folder, files['mtx_file']), 
				os.path.join(upload_folder, files['genes_file']), 
				os.path.join(upload_folder, files['barcodes_file']))

		return expr_df, meta_df

	def build_h5(self, expr_df=None, meta_df=None):
		'''Build an h5 file to enclose the expression and metadata.'''
		outfile = os.path.join(self.upload_folder, self.id +'.h5')
		if expr_df is None and meta_df is None:
			expr_df, meta_df = self.parse()
		try:
			f = h5py.File(outfile, 'w')
			# Add data
			data_grp = f.create_group('data')
			data_grp.create_dataset('expression', data=expr_df)
			# Add gene metadata
			gene_grp = f.create_group('meta/gene')
			gene_grp.create_dataset('symbol', data=[x.encode('utf-8') for x in expr_df.index], 
				dtype=h5py.special_dtype(vlen=str))
			# Add sample metadata
			sample_metadata_grp = f.create_group('meta/sample')
			for col in meta_df.columns:
				sample_metadata_grp.create_dataset(col, 
					data=meta_df[col].tolist())
			f.close()
		except Exception as e:
			print(e)
			os.unlink(outfile)
			outfile = None
		return outfile

	def upload_h5_to_cloud(self):
		'''Upload the h5 file to Google cloud storage for other apps to access.'''
		h5_file = os.path.join(self.upload_folder, self.id +'.h5')
		client = storage.Client()
		bucket = client.get_bucket('scavi-user-data')
		blob = bucket.blob('%s/%s.h5' % (self.id, self.id))
		blob.upload_from_filename(h5_file, content_type='text/html')
		blob.make_public()
		print('File uploaded to GCloud: ', 'https://storage.googleapis.com/scavi-user-data/%s/%s.h5' % (self.id, self.id))
		# Remove file
		os.unlink(h5_file)


	@classmethod
	def exists(cls, upload_id):
		doc = cls.db[cls.coll].find_one({'_id': ObjectId(upload_id)})
		return doc is not None

	@classmethod
	def load(cls, upload_id):
		doc = cls.db[cls.coll].find_one({'_id': ObjectId(upload_id)})
		obj = cls(doc['files'], save=False)
		obj.id = upload_id
		obj.started = doc['started']
		obj.done = doc['done']
		obj.error = doc.get('error', False)
		obj.e = doc.get('e', None)
		obj.dataset_id = doc.get('dataset_id', None)
		obj.type_ = doc.get('type', None)
		return obj

