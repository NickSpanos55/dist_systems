import requests
from flask import Flask, jsonify, request, render_template, redirect, Markup
from node import node
from bootstrap_node import bootstrap_node
import pickle
import threading
import time

app = Flask(__name__)

@app.route('/broadcast_transaction', methods=['POST'])
def rest_broadcast_transaction():
    transaction = pickle.loads(request.data)
    if node.verbose >= 2:
        print(f"Received Transaction")
    node.buffer_transaction.append(transaction)
    return "", 200

@app.route('/broadcast_block', methods=['POST'])
def rest_broadcast_block():
    block = pickle.loads(request.data)
    if node.verbose >= 2:
        print(f"Received Block")
    node.mining = False
    node.buffer_block.append(block)
    return "", 200

@app.route('/broadcast_blockchain', methods=['GET'])
def rest_broadcast_blockchain():
    node.broadcast_blockchain()
    return "", 200

@app.route('/receive_blockchain', methods=['POST'])
def rest_receive_blockchain():
    blockchain_data = pickle.loads(request.data)
    if node.verbose >= 2:
        print(f"Received Consensus-Blockchain")
    node.receive_blockchain(blockchain_data)
    return "", 200

@app.route('/node/get_ring', methods=['POST'])
def rest_get_ring():
    ring = pickle.loads(request.data)
    node.ring = ring
    node.public_utxo = {node_info[1]:[] for _, node_info in node.ring.items()}
    node.public_utxo_snapshot = {node_info[1]:[] for _, node_info in node.ring.items()}
    if node.verbose >= 2:
        print(f"Node Ring has been Updated")
    return "", 200

@app.route('/bootstrap/initialize', methods=['POST'])
def rest_insert_new_node():
    node_credentials = pickle.loads(request.data)
    new_node_id, capacity, difficulty, verbose = node.register_node_to_ring(node_credentials)

    if new_node_id == total_nodes-1:
        thread = threading.Thread(target=node.initialize, daemon=True)
        thread.start()

    print(f"New node added, with ID={new_node_id}")
    return {"id": new_node_id, "capacity": capacity, "difficulty": difficulty, "verbose": verbose}, 200

@app.route('/', methods=['GET'])
def frontend_redirect_to_index():
    return redirect("/frontend/index", code=302)

@app.route('/frontend/index', methods=['GET'])
def frontend_index():
    throughput, block_time = node.compute_metrics()
    return render_template("index.html", node_id=node.node_id,
                                         node_ip=":".join(node.address.split(':')[:-1]),
                                         node_port=node.address.split(':')[-1],
                                         no_of_nodes=len(node.ring),
                                         bc_difficulty=node.difficulty, 
                                         bc_capacity=node.capacity,
                                         bc_length=node.blockchain.get_chain_length(),
                                         throughput=round(throughput, 2),
                                         block_time=round(block_time, 2))

@app.route('/frontend/wallet', methods=['GET'])
def frontend_wallet():
    try:
        balances = dict()
        for i, pubkey in node.ring.items():
            if node.node_id == i:
                node_balance = node.wallet_balance(pubkey[1])
                node_public_key = Markup(pubkey[1].decode('utf-8').replace('\n', "<br>"))
                continue
            balances[i] = node.wallet_balance(pubkey[1])
        return render_template("wallet.html", balances=balances,
                                              node_balance=node_balance,
                                              node_public_key=node_public_key)
    except:
        return redirect("index", code=302)

@app.route('/consensus', methods=['GET','POST'])
def consensus():
    if request.method == "POST":
        token = pickle.loads(request.data)
        node.consensus.buffer_token.append(token)
        node.mining = False
        return "Passive Consensus", 200

@app.route('/start_consensus', methods=['GET','POST'])
def start_consensus():
    if request.method == "GET":
        node.consensus.start_passive()
        return "OK", 200

@app.route('/stop_consensus', methods=['GET','POST'])
def stop_consensus():
    if request.method == "GET":
        node.consensus.stop()
        return "OK", 200

@app.route('/frontend/send', methods=['GET','POST'])
def frontend_send():
    if request.method == "POST":
        receiver = request.form["receiver"]
        amount = request.form["amount"]
        try:
            node.buffer_create.append( (int(receiver), int(amount)) )
        except:
            pass
    return render_template("send.html")

@app.route('/frontend/view', methods=['GET'])
def frontend_view():
    try:
        transactions = node.view_transactions()
        return render_template("view.html", transactions=transactions)
    except:
        return redirect("index", code=302)

# run it once fore every node

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-bip', '--bootstrap_ip', default="127.0.0.1", type=str, help='bootstrap IP')
    parser.add_argument('-nip', '--node_ip', default="127.0.0.1", type=str, help='node IP')
    parser.add_argument('-np', '--node_port', default=5000, type=int, help='node port')
    parser.add_argument('-bp', '--bootstrap_port', default=5000, type=int, help='bootstrap port')
    parser.add_argument('-6', '--ipv6', action='store_true', help='ipv6 address')
    parser.add_argument('-m', '--mode', default=0, type=int, help='bootstrap or node node')
    parser.add_argument('-n', '--nodes', default=0, type=int, help='number of nodes in network')
    parser.add_argument('-c', '--capacity', default=1, type=int, help='capacity of block')
    parser.add_argument('-d', '--difficulty', default=5, type=int, help='difficulty of mine')
    parser.add_argument('-v', '--verbose', default=1, type=int, help='verbose of prints')

    args = parser.parse_args()
    node_ip = args.node_ip
    bootstrap_ip = args.bootstrap_ip
    ipv6 = args.ipv6
    node_port = args.node_port
    bootstrap_port = args.bootstrap_port
    mode = args.mode
    total_nodes = args.nodes
    capacity = args.capacity
    difficulty = args.difficulty
    verbose = args.verbose

    if ipv6 == 1:
        bootstrap_ip_brackets = "[" + bootstrap_ip + "]"
        node_ip_brackets = "[" + node_ip + "]"
    else:
        bootstrap_ip_brackets = bootstrap_ip
        node_ip_brackets = node_ip

    if mode == 1:
        node = bootstrap_node(f"{node_ip_brackets}:{node_port}", total_nodes, capacity, difficulty, verbose)
    else:
        node = node(f"{node_ip_brackets}:{node_port}", f"{bootstrap_ip_brackets}:{bootstrap_port}")

    def serve_buffer():
        while True:
            while node.consensus.active():
                if len(node.consensus.buffer_token)>0:
                    node.process_consensus_token(node.consensus.buffer_token.pop(0))

            if len(node.buffer_block)>0:
                ret = node.validate_block(node.buffer_block[0])

                if ret == 0:
                    node.create_new_block()
                    node.buffer_block.pop(0)
                if ret == 1:
                    if len(node.current_block.listOfTransactions) == node.capacity:
                        node.mine_block()
                    node.buffer_block.pop(0)
                if ret == 2:
                    for node_id, node_info in node.ring.items():    
                        if node_id == node.node_id:
                            continue
                        r = requests.get(f"http://{node_info[0]}/start_consensus")
                    next_node_id = (node.node_id + 1) % len(node.ring)
                    node.consensus.start_active(node.blockchain.get_chain_length(), node.node_id, node.ring[next_node_id][0])
                    
            elif len(node.buffer_transaction)>0:
                item = node.buffer_transaction[0]
                if node.validate_transaction(item):
                    node.add_transaction_to_block(item)
                node.buffer_transaction.pop(0)

            elif len(node.buffer_create)>0:
                item = node.buffer_create[0]
                try:
                    node.create_transaction(node.ring[item[0]][1], item[1])
                except:
                    pass
                node.buffer_create.pop(0)
        return None

    thread = threading.Thread(target=serve_buffer, daemon=True)
    thread.start()

    app.run(host=node_ip, port=node_port, debug=False, use_reloader=False, processes=1)