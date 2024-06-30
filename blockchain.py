import hashlib
import json
from time import time
from uuid import uuid4
from textwrap import dedent
import requests
from urllib.parse import urlparse
from flask import Flask, jsonify, request


class Blockchain(object):

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        # Creates a new block and adds it to the chain
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    """
    The idea is that each new block contains within itself, the hash of the previous block.
    This is crucial because this is what gives the blockchain immutability
    """

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined block.
        :param sender: Address of the sender
        :param recipient: Address of the recipient
        :param amount: Amount
        :return: The index of the block that will hold its transactions
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        # Returns the last block in the chain
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a block
        :param block: <dict> block
        :return: <str>
        We must also make sure that the Dictionary is ordered otherwise we will have inconsistent hashes.
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work algorithm
        Finds a number p such that hash(pp') contains leading 4 zeros, where p
        is the previous proof and p' is the final proof.
        :param last_proof: <int>
        :return: <int>
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the proof: Does hash(last_proof, proof) contain 4 leading zeros?
        :param last_proof: <int> Previous proof
        :param proof: <int> Current proof
        :return: <bool>
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        """
        Adds a new node to the list of the nodes.
        :param address: <str> Address of the node.
        :return: None
        """
        parsedURL = urlparse(address)
        self.nodes.add(parsedURL.netloc)

    def valid_chain(self, chain):
        """
        Determines if a given blockchain is valid.
        :param chain: <list> A blockchain
        :return: True if valid, False otherwise.
        """
        last_block = chain[0]
        curr_index = 1
        while curr_index < len(chain):
            block = chain[curr_index]
            print(f'{last_block}')
            print(f'{block}')
            print('\n-----------\n')
            # Checking that the hash of the block is correct.
            if block['previous_hash'] != self.hash(last_block):
                return False
            # Checking that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False
            last_block = block
            curr_index += 1
        return True


# Instantiating the node.
mdzdmr = Flask(__name__)

# Generating a globally unique address for this node.
node_identifier = str(uuid4()).replace('-', '')

# Instantiating the blockchain
blockchain = Blockchain()


@mdzdmr.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof.
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)
    # We must receive a reward for finding the proof.
    # The sender is '0' to signify that this node has mined a coin.
    blockchain.new_transaction(sender='0', recipient=node_identifier, amount=1)
    # Forge the new block by adding it to the chain.
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@mdzdmr.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()
    # Check that the required fields are in the POST'ed data.
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return "Missing values", 400
    # Creating a new transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added to block {index}'}
    return jsonify(response), 201


@mdzdmr.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


if __name__ == '__main__':
    mdzdmr.run(host='0.0.0.0', port=5000)
