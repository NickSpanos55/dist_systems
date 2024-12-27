# import blockchain
import time
import pickle
from Crypto.Hash import SHA256

class Block:
    def __init__(self, previousHash, genesis=False):
        ##set

        self.timestamp = time.time()
        self.previousHash = previousHash
        self.listOfTransactions = []
        self.nonce = 0
        self.hash = 0

        self.block_len = 0
        self.genesis = genesis
    
    def myHash(self, nonce):
        #calculate self.hash
        block_hash = SHA256.new()
        block_hash.update(pickle.dumps(self.to_dict(nonce)))
        return block_hash.digest()

    def setHash(self, computed_hash):
        self.hash = computed_hash
        return None

    def setNonce(self, nonce):
        self.nonce = nonce
        return None

    def to_dict(self, nonce):
        return {"timestamp": self.timestamp,
                "previousHash": self.previousHash,
                "listOfTransactions": sorted(self.listOfTransactions),
                "nonce": nonce}

    def add_transaction(self, transaction):
        #add a transaction to the block
        self.listOfTransactions.append(transaction)
        self.block_len += 1

    def __gt__(self, other):
        if(self.timestamp > other.timestamp):
            return True
        else:
            return False