import block
import pickle

class Blockchain:
	def __init__(self):

		self.chain = []

	def add_block(self,block):
		self.chain.append(block)

	def get_last_hash(self):
		return self.chain[-1].hash 

	def get_chain_length(self):
		return len(self.chain)

	def to_pickle(self):
		return pickle.dumps(self)

	def view_last_transactions(self):
		last_transactions = []
		for transaction in self.chain[-1].listOfTransactions:
			last_transactions.append( (transaction.sender_address, transaction.receiver_address, transaction.amount) )
		return last_transactions