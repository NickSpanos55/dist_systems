import requests
import wallet
import transaction
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import blockchain
import pickle
import block
import random
import copy
import consensus
import node
import time

class bootstrap_node(node.node):
    def __init__(self, address, total_nodes=0, capacity=1, difficulty=5, verbose=1):
        self.wallet = self.create_wallet()
        self.node_id = 0

        self.address = address
        self.total_nodes = total_nodes
        self.capacity = capacity
        self.difficulty = difficulty
        self.verbose = verbose

        self.registered_nodes = 0
        self.node_id = 0
        self.public_utxo = dict()                                       # {public_key: [(utxo_id, transaction_id, self.public_key, amount)]}
        self.public_utxo_snapshot = dict()
        self.ring = {0: (self.address, self.wallet.public_key)}         # {id: (address, public_key)}   #here we store information for every node, as its id, its address (ip:port) its public key

        self.current_block = None
        self.mining = False

        self.blockchain = blockchain.Blockchain()

        self.consensus = consensus.Consensus()

        self.buffer_transaction = []
        self.buffer_block = []
        self.buffer_create = []

    def broadcast_ring(self):
        for node, node_info in self.ring.items():
            if node == 0: continue
            r = requests.post(f"http://{node_info[0]}/node/get_ring", data=pickle.dumps(self.ring))

    def register_node_to_ring(self, node_credentials):
        self.registered_nodes += 1
        self.ring[self.registered_nodes] = (node_credentials[0], node_credentials[1])
        return self.registered_nodes, self.capacity, self.difficulty, self.verbose

    def initialize(self):
        time.sleep(2)
        self.broadcast_ring()
        self.public_utxo = {node_info[1]:[] for _, node_info in self.ring.items()}
        self.public_utxo_snapshot = {node_info[1]:[] for _, node_info in self.ring.items()}
        self.create_genesis(self.total_nodes)

        time.sleep(2)
        for node_id, node_info in self.ring.items():
            if node_id != self.node_id:
                r = requests.post(f"http://{self.ring[0][0]}/frontend/send", data={'receiver': node_id, 'amount': 100})

       # _ = requests.post(f"http://127.0.0.1:4999/start_test_transactions", data=pickle.dumps(self.ring))

        return None

    def create_genesis(self, total_nodes):
        genesis_transaction = transaction.Transaction(self.wallet.public_key, self.wallet.private_key, self.wallet.public_key, total_nodes*100, [], genesis=True)
        genesis_block = block.Block(1, genesis=True)
        genesis_block.add_transaction(genesis_transaction)
        genesis_block.setHash(genesis_block.myHash(0))
        self.broadcast_block(genesis_block)
        return None