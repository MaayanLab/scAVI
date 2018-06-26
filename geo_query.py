'''
Utils for using GEOquery r package through rpy2 and 
parsing metadata from GEO.
'''

import os, sys
import codecs
from collections import defaultdict
import rpy2.robjects as ro

ro.r('''
library(GEOquery)

download_meta <- function(geo_id) {
	# geo_id: 
	soft <- getGEOfile(GEO=geo_id, amount='quick')
	soft
}

download_gse <- function(gse_id) {
	gse <- getGEO(gse_id, GSEMatrix = F, getGPL = F)
	gse
}

retrieve_gse_meta <- function(gse){
	Meta(gse)
}

retrieve_gsms_meta_from_gse <- function(gse) {
	gsm_metas <- lapply(GSMList(gse), function(x) {Meta(x)})
	gsm_metas
}

''')

download_meta = ro.globalenv['download_meta']
download_gse = ro.globalenv['download_gse']
retrieve_gse_meta = ro.globalenv['retrieve_gse_meta']
retrieve_gsms_meta_from_gse = ro.globalenv['retrieve_gsms_meta_from_gse']

def _parse_soft(f):
	obj = {}
	for line in f:
		if line.startswith('!') and '=' in line:
			sl = line.split(' = ')
			if len(sl) == 2:
				key = sl[0].strip('!')
				val = sl[1].strip()
				if key not in obj:
					obj[key] = [val]
				else:
					obj[key].append(val)
	
	for key, val in obj.items():
		if len(val) == 1: # unpack list if only 1 item
			obj[key] = val[0] 
	return obj

def parse_soft(fn):
	'''
	parse the metadata in soft file download by `download_meta`
	'''
	try:
		f = codecs.open(fn, 'r', 'ISO-8859-1')
		obj = _parse_soft(f)
	except Exception as e:
		print e
		f = open(fn, 'r')
		obj = _parse_soft(f)
	finally:
		return obj

def download_and_parse_meta(geo_id):
	fn = list(download_meta(geo_id))[0]
	obj = parse_soft(fn)
	return obj


def _unpack_singles(x):
	x = list(x)
	if len(x) == 1:
		x = x[0]
	return x


def convert_r_list(rlist):
	keys = list(rlist.names)
	values = map(_unpack_singles, rlist)
	d = dict(zip(keys, values))
	return d

def convert_gsms_meta_r_list(gsm_metas):
	'''
	Convert the R nested list to a python nested dict
	'''
	gsms = list(gsm_metas.names)
	parsed_d = {}
	for gsm, gsm_meta in zip(gsms, gsm_metas):
		sub_d = convert_r_list(gsm_meta)
		parsed_d[gsm] = sub_d
	return parsed_d


def drop_duplicated_meta_in_gsm(gse_meta, gsm_metas):
	'''
	Filter out key: values pairs in gsm_metas that are redundant with gse_meta
	'''
	gsm_metas_filtered = defaultdict(lambda : {})
	for gsm, gsm_meta in gsm_metas.items():
		for key, value in gsm_meta.items():
			if gse_meta.get(key) != value:
				gsm_metas_filtered[gsm][key] = value

	return gsm_metas_filtered


