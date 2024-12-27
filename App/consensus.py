import requests
import pickle
import datetime
import time

class Token:
    def __init__(self, sender_chain_length, sender_id):
        self.max_chain_length = sender_chain_length
        self.max_node_id = sender_id
        self.sender_id = sender_id

    def __str__(self):
        timestp = datetime.datetime.utcnow().strftime("%a %b %d %H:%M:%S %Z %Y")
        return f"[{timestp}] Token - Sender: {self.sender_id} - Candidate: {self.max_node_id} - Chain: {self.max_chain_length}"

    def to_pickle(self):
        return pickle.dumps(self)

    def update_token(self, node_chain_length, node_id):
        if node_chain_length > self.max_chain_length:
            self.max_chain_length = node_chain_length
            self.max_node_id = node_id
            return None
        elif (node_chain_length == self.max_chain_length) and (node_id < self.max_node_id):
            self.max_chain_length = node_chain_length
            self.max_node_id = node_id
            return None
        else:
            return None

class Consensus:
    def __init__(self):
        self.consensus = False
        self.consensus_sender = False
        self.len_validated_chain = 0
        self.utxo_state = dict()
        self.buffer_token = []

    def start_active(self, node_chain_length, node_id, next_node_address):
        self.consensus_sender = True
        self.consensus = True
        token = Token(node_chain_length, node_id)
        r = requests.post(f"http://{next_node_address}/consensus", data=token.to_pickle())

    def start_passive(self):
        self.consensus = True

    def stop(self):
        self.buffer_token = []
        self.consensus_sender = False
        self.consensus = False

    def active(self):
        return self.consensus
    
    def not_active(self):
        return not self.consensus