'''
Encrypt and decrypt a string
'''

# from Crypto.Cipher import AES
# from Crypto import Random
# secrete_key = b'Sixteen byte key'
# iv = Random.new().read(AES.block_size)
# cipher = AES.new(secrete_key, AES.MODE_CFB, iv)


# def aes_encrypt(s):
# 	msg = iv + cipher.encrypt(s)
# 	return msg.encode('hex')

# def aes_decrypt(s):
# 	return cipher.decrypt(s.decode("hex"))[len(iv):]


def aes_encrypt(s):
	return s.encode('hex')

def aes_decrypt(s):
	return s.decode('hex')
