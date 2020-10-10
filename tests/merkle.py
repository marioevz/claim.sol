import math
import web3
from hexbytes import HexBytes

Web3 = web3.Web3()

class MerkleTree():

    @staticmethod
    def get_elem_hash(index, elem):
        types = [x['type'] for x in elem]
        values = [x['value'] for x in elem]
        types.insert(0, 'uint256')
        values.insert(0, index)
        return Web3.solidityKeccak(types, values)

    @staticmethod
    def get_hashes_hash(hash1, hash2):
        if int(hash2.hex(),16) < int(hash1.hex(), 16):
            return Web3.solidityKeccak(['bytes32'] * 2, [hash2, hash1])
        return Web3.solidityKeccak(['bytes32'] * 2, [hash1, hash2])

    @staticmethod
    def get_pad():
        return HexBytes('0x' + 'ff' * 32)

    @staticmethod
    def get_next_pow_two(n):
        return int(math.pow(2, math.ceil(math.log2(n))))

    def __init__(self, l):

        self.elements = l

        self.hashes = [MerkleTree.get_elem_hash(x, self.elements[x]) for x in range(len(self.elements))]

        # We need to make sure the tree is complete
        while len(self.hashes) != MerkleTree.get_next_pow_two(len(self.hashes)):
            self.hashes.append(MerkleTree.get_pad())

        self.leaf_count = len(self.hashes)
        
        i = 0
        while i + 1 < len(self.hashes):
            self.hashes.append(MerkleTree.get_hashes_hash(self.hashes[i], self.hashes[i+1]))
            i += 2

        self.root = self.hashes[-1]

    def get_elem_index(self, elem):
        pass

    def get_proof(self, elem):
        return self.get_proof_by_idx(self.get_elem_index(elem))

    @staticmethod
    def get_proof_indexes(idx, leaf_count):
        indexes = []
        prev_lvl_widths = []
        while leaf_count > 1:
            indexes.append(sum(prev_lvl_widths) + idx + (1 if idx % 2 == 0 else -1))
            prev_lvl_widths.append(leaf_count)
            idx //= 2
            leaf_count //= 2
        return indexes # + [sum(prev_lvl_widths)] Don't include root

    def get_proof_by_idx(self, idx):
        if idx >= len(self.elements) or idx < 0:
            raise Exception("Index out of bounds")

        proof_indexes = MerkleTree.get_proof_indexes(idx, self.leaf_count)

        return [self.hashes[x].hex() for x in proof_indexes]