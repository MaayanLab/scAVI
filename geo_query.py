'''
Utils for using GEOquery r package through rpy2 and 
parsing metadata from GEO.
'''

import os, sys
import codecs
import rpy2.robjects as ro

ro.r('''
library(GEOquery)

download_meta <- function(geo_id) {
	# geo_id: 
	soft <- getGEOfile(GEO=geo_id, amount='quick')
	soft
}
''')

download_meta = ro.globalenv['download_meta']

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

