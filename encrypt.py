'''
Encrypt and decrypt a string
'''

def encrypt(s):
	return s.encode('hex')

def decrypt(s):
	return s.decode('hex')
