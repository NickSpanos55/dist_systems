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
import time

green = '\033[92m'
red = '\033[91m'
white = '\033[0m'
yellow = '\033[93m'
purple = "\033[0;35m"
brown = "\033[0;33m"

class node:
    def __init__(self, address, bootstrap_address):
        self.wallet = self.create_wallet()
        self.node_id = 0

        self.address = address
        self.bootstrap_address = bootstrap_address
        self.ring = dict()          # {id: (address, public_key)}   #here we store information for every node, as its id, its address (ip:port) its public key

        self.public_utxo = dict()   # {public_key: [(utxo_id, transaction_id, self.public_key, amount)]}
        self.public_utxo_snapshot = dict()

        r = requests.post(f"http://{self.bootstrap_address}/bootstrap/initialize", data=pickle.dumps( {0: self.address, 1: self.wallet.public_key}) )
        self.node_id = r.json()["id"]
        self.capacity = r.json()["capacity"]
        self.difficulty = r.json()["difficulty"]
        self.verbose = r.json()["verbose"]
        print(f"Received ID={self.node_id}")
        print(f"Received Capacity={self.capacity}")
        print(f"Received Difficulty={self.difficulty}")

        self.current_block = None
        self.mining = False

        self.blockchain = blockchain.Blockchain()

        self.consensus = consensus.Consensus()

        self.buffer_transaction = []
        self.buffer_block = []
        self.buffer_create = []

    def create_wallet(self):
        return wallet.wallet()

    def create_transaction(self, receiver_public_key, value):
        if self.verbose >= 1:
            print(green+"[Enter] create_transaction"+white)
        #remember to broadcast it

        if value < 0:
            print("ERROR: Transaction Value must be Non-Negative")
            if self.verbose >= 1:
                print(red+"[Exit] create_transaction"+white)
            return False

        transaction_inputs = []
        nbc_counter = 0
        for utxo in self.public_utxo[self.wallet.public_key]:
            nbc_counter += utxo[3]
            transaction_inputs.append(utxo)
            if nbc_counter >= value:
                break

        if nbc_counter < value:
            print("ERROR: Not enough balance for Transaction")
            if self.verbose >= 1:
                print(red+"[Exit] create_transaction"+white)
            return False

        new_transaction = transaction.Transaction(self.wallet.public_key, self.wallet.private_key, receiver_public_key, value, transaction_inputs)
        self.broadcast_transaction(new_transaction)
        if self.verbose >= 1:
            print(red+"[Exit] create_transaction"+white)
        return True

    def broadcast_transaction(self, transaction):
        if self.verbose >= 1:
            print(green+"[Enter] broadcast_transaction"+white)

        for node_id, node_info in self.ring.items():    
            if node_id == self.node_id:
                continue
            r = requests.post(f"http://{node_info[0]}/broadcast_transaction", data=pickle.dumps(transaction))

        self.buffer_transaction.append(transaction)
        if self.verbose >= 1:
            print(red+"[Exit] broadcast_transaction"+white)
        return None

    def verify_signature(self, transaction):
        if self.verbose >= 2:
            print(green+"[Enter] verify_signature"+white)
        transaction_hash = SHA256.new()
        transaction_hash.update(pickle.dumps(transaction.to_dict()))

        cipher = PKCS1_v1_5.new(RSA.import_key(transaction.sender_address))
        if self.verbose >= 2:
            print(red+"[Exit] verify_signature"+white)
        try:
            cipher.verify(transaction_hash, transaction.signature)
            return True
        except ValueError:
            return False

    def validate_transaction(self, transaction):
        if self.verbose >= 1:
            print(green+"[Enter] validate_transaction"+white)

        if not transaction.genesis:
            
            if not self.verify_signature(transaction):
                print("ERROR: Transaction Signature is Invalid")
                return False

            nbc_counter = 0
            for transaction_input in transaction.transaction_inputs:
                if transaction_input not in self.public_utxo[transaction.sender_address]:
                    print("ERROR: Inputs not in utxos")
                    return False
                nbc_counter += transaction_input[3]

            if nbc_counter < transaction.amount:
                print("ERROR: Inputs not enough for Amount Spent")
                return False
   
        if not transaction.genesis:
            for transaction_input in transaction.transaction_inputs:
                self.public_utxo[transaction.sender_address].remove(transaction_input)

            self.public_utxo[transaction.sender_address].append(transaction.transaction_outputs[1])

        self.public_utxo[transaction.receiver_address].append(transaction.transaction_outputs[0])

        if self.verbose >= 1:
            print(red+"[Exit] validate_transaction"+white)
        return True

    def wallet_balance(self, public_key):
        return sum(utxo[3] for utxo in self.public_utxo[public_key])

    def create_new_block(self):
        if self.verbose >= 2:
            print(green+"[Enter] create_new_block"+white)
        self.current_block = block.Block(self.blockchain.get_last_hash())
        if self.verbose >= 2:
            print(red+"[Exit] create_new_block"+white)
        return None

    def add_transaction_to_block(self, transaction):
        if self.verbose >= 2:
            print(green+"[Enter] add_transaction_to_block"+white)

        self.current_block.add_transaction(transaction)
        if self.current_block.block_len == self.capacity:
            self.mine_block()

        if self.verbose >= 2:
            print(red+"[Exit] add_transaction_to_block"+white)
        return None

    def mine_block(self):
        if self.verbose >= 1:
            print(green+"[Enter] mine_block"+white)
        self.mining = True
        target_string = "0" * self.difficulty
        while self.mining:
            nonce = random.randint(0, 4_294_967_295) # 4-byte uint nonce
            h = self.current_block.myHash(nonce)

            # h_str = format(int.from_bytes(h, byteorder="little"), '#078')         # for Decimal
            # h_str = format(int.from_bytes(h, byteorder="little"), '#0258b')[2:]   # for Binary
            h_str = format(int.from_bytes(h, byteorder="little"), '#066x')[2:]    # for Hex
            if h_str[:self.difficulty] == target_string:
                if self.verbose >= 1:
                    print(yellow+"[Mine] Block mined by me"+white)
                self.current_block.setHash(h)
                self.current_block.setNonce(nonce)
                self.broadcast_block(self.current_block)
                break
        if self.verbose >= 1:
            print(red+"[Exit] mine_block"+white)
        return None

    def broadcast_block(self, current_block):
        if self.verbose >= 2:
            print(green+"[Enter] broadcast_block"+white)
        for node_id, node_info in self.ring.items():
            if node_id == self.node_id:
                continue
            r = requests.post(f"http://{node_info[0]}/broadcast_block", data=pickle.dumps(current_block))
        self.buffer_block.append(current_block)
        if self.verbose >= 2:
            print(red+"[Exit] broadcast_block"+white)
        return None

    def validate_block(self, block):
        if self.verbose >= 1:
            print(green+"[Enter] validate_block"+white)

        if not block.genesis:
            if self.blockchain.get_last_hash() != block.previousHash:
                # consensus
                return 2

            h = block.myHash(block.nonce)
            h_str = format(int.from_bytes(h, byteorder="little"), '#078')
            if int(h_str[:self.difficulty]) != 0:
                print("ERROR: Block nonce is not valid")
                return 1

        public_utxo_temp = copy.deepcopy(self.public_utxo)

        self.public_utxo = copy.deepcopy(self.public_utxo_snapshot)

        for transaction in block.listOfTransactions:
            if not self.validate_transaction(transaction):
                self.public_utxo = copy.deepcopy(public_utxo_temp)
                print("ERROR: Block was not validated")
                if self.verbose >= 1:
                    print(red+"[Exit] validate_block"+white)
                return 1

        self.blockchain.add_block(block)

        self.public_utxo_snapshot = copy.deepcopy(self.public_utxo)

        if block.genesis:
            self.consensus.len_validated_chain = 1
            self.consensus.utxo_state = copy.deepcopy(self.public_utxo)
        
        if self.verbose >= 1:
            print(red+"[Exit] validate_block"+white)
        return 0


    #consensus functions
    def node_rollback(self):
        self.public_utxo = copy.deepcopy(self.consensus.utxo_state)
        self.public_utxo_snapshot = copy.deepcopy(self.consensus.utxo_state)
        self.blockchain.chain = self.blockchain.chain[:self.consensus.len_validated_chain]
        self.mining = False
        self.buffer_transaction = []
        self.buffer_block = []

    def process_consensus_token(self, token):
        if self.verbose >= 1:
            print(green+"[Enter] process_consensus_token"+white)

        if self.consensus.consensus_sender and (token.sender_id > self.node_id):

            if self.verbose >= 1:
                print(red+"[Exit] process_consensus_token"+white)
            return None

        if self.consensus.consensus_sender and (token.sender_id == self.node_id):
            r = requests.get(f"http://{self.ring[token.max_node_id][0]}/broadcast_blockchain")
            if self.verbose >= 1:
                print(red+"[Exit] process_consensus_token"+white)
            return None

        token.update_token(self.blockchain.get_chain_length(), self.node_id)

        next_node_id = (self.node_id + 1) % len(self.ring)
        r = requests.post(f"http://{self.ring[next_node_id][0]}/consensus", data=token.to_pickle())
        if self.verbose >= 1:
            print(red+"[Exit] process_consensus_token"+white)
        return None

    def broadcast_blockchain(self):
        if self.verbose >= 1:
            print(green+"[Enter] broadcast_blockchain"+white)


        blockchain_data = (self.blockchain.chain, self.current_block, self.buffer_transaction)
        for node_id, node_info in self.ring.items():
            if node_id == self.node_id:
                self.mining = False
                self.buffer_block = []
                self.consensus.utxo_state = copy.deepcopy(self.public_utxo_snapshot)
                self.consensus.len_validated_chain = len(self.blockchain.chain)
                continue
            else:
                r = requests.post(f"http://{node_info[0]}/receive_blockchain", data=pickle.dumps(blockchain_data))


        for node_id, node_info in self.ring.items():
            if node_id == self.node_id:
                continue
            else:
                r = requests.get(f"http://{node_info[0]}/stop_consensus")

        self.consensus.stop()
        

        if len(self.current_block.listOfTransactions) == self.capacity:
            self.mine_block()

        if self.verbose >= 1:
            print(red+"[Exit] broadcast_blockchain"+white)
        return None

    def receive_blockchain(self, blockchain_data):
        time.sleep(0.1)
        if self.verbose >= 1:
            print(green+"[Enter] receive_blockchain"+white)
        temp_verbose = self.verbose
        self.verbose = 0

        blockchain_temp = copy.deepcopy(self.blockchain)
        public_utxo_temp = copy.deepcopy(self.public_utxo)
        public_utxo_snapshot_temp = copy.deepcopy(self.public_utxo_snapshot)

        self.public_utxo_snapshot = copy.deepcopy(self.consensus.utxo_state)
        self.blockchain.chain = self.blockchain.chain[:self.consensus.len_validated_chain]
        self.mining = False
        self.buffer_transaction = []
        self.buffer_block = []


        for block in blockchain_data[0][self.consensus.len_validated_chain:]:        
            temp = self.validate_block(block)
            if temp==1 or temp==2:
                self.blockchain = copy.deepcopy(blockchain_temp)
                self.public_utxo_snapshot = copy.deepcopy(public_utxo_snapshot_temp)
                return False


        self.consensus.utxo_state = copy.deepcopy(self.public_utxo)
        self.consensus.len_validated_chain = len(self.blockchain.chain)

        self.create_new_block()
        self.buffer_transaction = copy.deepcopy(blockchain_data[1].listOfTransactions + blockchain_data[2])

        self.verbose = temp_verbose    
        if self.verbose >= 1:
            print(red+"[Exit] receive_blockchain"+white)


        return True

    def view_transactions(self):
        pub_to_id = {v[1]:k for k,v in self.ring.items()}
        last_transactions = []
        for transaction in self.blockchain.view_last_transactions():
            last_transactions.append( (pub_to_id[transaction[0]], pub_to_id[transaction[1]], transaction[2]) )
        return last_transactions

    def compute_metrics(self):
        try:
            last_transaction_time = self.blockchain.chain[-1].listOfTransactions[-1].timestamp
            first_transaction_time = self.blockchain.chain[0].listOfTransactions[0].timestamp
            throughput = ( (self.blockchain.get_chain_length() * self.capacity) - 1 ) / (last_transaction_time - first_transaction_time)
        except:
            throughput = 0

        try:
            last_block_time = self.blockchain.chain[-1].timestamp
            first_block_time = self.blockchain.chain[0].timestamp
            block_time = ( last_block_time -  first_block_time ) / (self.blockchain.get_chain_length() - 1)
        except:
            block_time = 0

        return throughput, block_time