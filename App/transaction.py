import pickle
import time
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from uuid import uuid4

class Transaction:

    def __init__(self, sender_public_key, sender_private_key, receiver_public_key, amount, transaction_inputs, genesis=False):
        self.timestamp = time.time()
        self.genesis = genesis
        self.sender_address = sender_public_key
        self.receiver_address = receiver_public_key
        self.amount = amount
        self.transaction_inputs = transaction_inputs
        self.transaction_id = self.create_transaction_id()
        self.transaction_outputs = self.create_transaction_outputs()
        self.signature = self.sign_transaction(sender_private_key)

    def to_dict(self):
        return {"sender_address": self.sender_address,
                "receiver_address": self.receiver_address,
                "amount": self.amount,
                "transaction_id": self.transaction_id,
                "transaction_inputs": self.transaction_inputs,
                "transaction_outputs": self.transaction_outputs}

    def to_dict_trans_id(self):
        return {"sender_address": self.sender_address,
                "receiver_address": self.receiver_address,
                "amount": self.amount,
                "transaction_inputs": self.transaction_inputs}

    def sign_transaction(self, sender_private_key):
        """
        Sign transaction with private key
        """
        transaction_hash = SHA256.new()
        transaction_hash.update(pickle.dumps(self.to_dict()))
        cipher = PKCS1_v1_5.new(RSA.import_key(sender_private_key))
        signature = cipher.sign(transaction_hash)
        return signature

    def create_transaction_id(self):
        h = SHA256.new()
        h.update(pickle.dumps(self.to_dict_trans_id()))
        return h.digest()

    def create_transaction_outputs(self):
        total_amount = 0
        for transaction_input in self.transaction_inputs:
            total_amount += transaction_input[3]

        sender_output = (uuid4(), self.transaction_id, self.sender_address, total_amount-self.amount)
        receiver_output = (uuid4(), self.transaction_id, self.receiver_address, self.amount)

        return [receiver_output, sender_output]

    def __gt__(self, other):
        if(self.transaction_id > other.transaction_id):
            return True
        else:
            return False

    def to_str(self, ring):
        pub_to_id = {v[1]:k for k,v in ring.items()}
        return f"{pub_to_id[self.sender_address]} -> {pub_to_id[self.receiver_address]} : {self.amount} - {self.transaction_id[:5]}"