import numpy as np

def nan_to_none(x):
	'''Convert np.nan to None.'''
	try:
		if np.isnan(x):
			x = None
	except TypeError:
		pass
	return x
