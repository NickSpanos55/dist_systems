import binascii

import Crypto
import Crypto.Random
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

import hashlib
from Crypto.PublicKey import RSA

class wallet:

	def __init__(self):
		key = RSA.generate(1024)
		self.private_key = key.export_key()
		self.public_key = key.publickey().export_key()