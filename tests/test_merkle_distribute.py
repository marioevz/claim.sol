import pytest
import math
from hexbytes import HexBytes
from brownie import MerkleClaim, ERC20, accounts, web3, reverts


ethAddress = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'

class MerkleTree():

    @staticmethod
    def get_elem_hash(index, elem):
        types = [x['type'] for x in elem]
        values = [x['value'] for x in elem]
        types.insert(0, 'uint256')
        values.insert(0, index)
        return web3.solidityKeccak(types, values)

    @staticmethod
    def get_hashes_hash(hash1, hash2):
        if int(hash2.hex(),16) < int(hash1.hex(), 16):
            return web3.solidityKeccak(['bytes32'] * 2, [hash2, hash1])
        return web3.solidityKeccak(['bytes32'] * 2, [hash1, hash2])

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
        return indexes + [sum(prev_lvl_widths)]

    def get_proof_by_idx(self, idx):
        if idx >= len(self.elements) or idx < 0:
            raise Exception("Index out of bounds")

        proof_indexes = MerkleTree.get_proof_indexes(idx, self.leaf_count)

        return [self.hashes[x] for x in proof_indexes]

def int_to_hex(i, byte_length):
    if isinstance(i, str):
        if i.startswith('0x'):
            i = int(i,16)
        else:
            i = int(i)
    return (hex(i)[2:]).zfill(byte_length * 2)

def hex_pack(to, token, amount, nonce):
    retstr = int_to_hex(to, 20)
    retstr += int_to_hex(token, 20)
    retstr += int_to_hex(amount, 32)
    retstr += int_to_hex(nonce, 32)
    return '0x' + retstr


def get_balance(tokens, currency, account):
    if currency == ethAddress:
        return account.balance()
    else:
        return tokens[currency].balanceOf(account.address)

@pytest.fixture
def claim_contract():
    return accounts[0].deploy(MerkleClaim)

@pytest.fixture
def tokens():
    t1 = ERC20.deploy("Test Token 1", "TST", {'from': accounts[0]})
    t2 = ERC20.deploy("Test Token 2", "TST", {'from': accounts[0]})
    t1.mint(accounts[0].address, web3.toWei(10,'ether'), {'from': accounts[0]})
    t1.mint(accounts[2].address, web3.toWei(10,'ether'), {'from': accounts[0]})
    t2.mint(accounts[1].address, web3.toWei(10,'ether'), {'from': accounts[0]})
    return {t1.address: t1, t2.address: t2}

@pytest.mark.parametrize('currency', [
    ethAddress,
    0])
def test_distribute_ether(claim_contract, tokens, currency):

    if currency != ethAddress:
        currency = list(tokens.keys())[currency]

    distributeTree = MerkleTree([
        [
            {
                'type':'address',
                'value': accounts[1].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(1,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[2].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(2,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[3].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(3,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[4].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(4,'ether')
            }
        ],
    ])

    if currency == ethAddress:
        claim_contract.distribute(currency, distributeTree.root, web3.toWei(10,'ether'), {"from": accounts[0], "value": web3.toWei(10,'ether')})
        #accounts[0].transfer(claim_contract.address, "10 ether", gas_price=0)
        #accounts[2].transfer(claim_contract.address, "10 ether", gas_price=0)
        # Burn the rest
        #accounts[0].transfer("0x0000000000000000000000000000000000000000", "90 ether", gas_price=0)
        #accounts[2].transfer("0x0000000000000000000000000000000000000000", "90 ether", gas_price=0)
    else:
        tokens[currency].approve(claim_contract.address, web3.toWei(10,'ether'), {"from": accounts[0]})
        claim_contract.distribute(currency, distributeTree.root, web3.toWei(10,'ether'), {"from": accounts[0]})

    assert "10 ether" == get_balance(tokens, currency, claim_contract)
    
    prev_balance = get_balance(tokens, currency, accounts[1])

    claim_contract.claim(currency, accounts[1].address, [x.hex() for x in distributeTree.get_proof_by_idx(0)], 0, web3.toWei(1,'ether'), {"from": accounts[1], "gas_price": 0})

    assert get_balance(tokens, currency, accounts[1]) == prev_balance + web3.toWei(1,'ether')
    

    with reverts("already claimed"):
        # Try to reuse proof, will fail due to the bitmap check
        claim_contract.claim(currency, accounts[1].address, [x.hex() for x in distributeTree.get_proof_by_idx(0)], 0, web3.toWei(1,'ether'), {"from": accounts[1], "gas_price": 0})

    with reverts("invalid proof"):
        # Try to claim with proper amount and index but invalid address, hence invalid proof
        claim_contract.claim(currency, accounts[1].address, [x.hex() for x in distributeTree.get_proof_by_idx(1)], 1, web3.toWei(2,'ether'), {"from": accounts[1], "gas_price": 0})

    # Correctly claim with following index
    prev_balance = get_balance(tokens, currency, accounts[2])
    claim_contract.claim(currency, accounts[2].address, [x.hex() for x in distributeTree.get_proof_by_idx(1)], 1, web3.toWei(2,'ether'), {"from": accounts[2], "gas_price": 0})
    assert get_balance(tokens, currency, accounts[2]) == prev_balance + web3.toWei(2,'ether')

    # Correctly claim with index out of order
    prev_balance = get_balance(tokens, currency, accounts[4])
    claim_contract.claim(currency, accounts[4].address, [x.hex() for x in distributeTree.get_proof_by_idx(3)], 3, web3.toWei(4,'ether'), {"from": accounts[4], "gas_price": 0})
    assert get_balance(tokens, currency, accounts[4]) == prev_balance + web3.toWei(4,'ether')

    # Correctly claim remaining index with other account
    prev_balance = get_balance(tokens, currency, accounts[3])
    claim_contract.claim(currency, accounts[3].address, [x.hex() for x in distributeTree.get_proof_by_idx(2)], 2, web3.toWei(3,'ether'), {"from": accounts[1], "gas_price": 0})
    assert get_balance(tokens, currency, accounts[3]) == prev_balance + web3.toWei(3,'ether')
    
    """ 
    sgn1 = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(1,'ether'), 1)
    sgn2 = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(2,'ether'), 2)

    signatures = sign_bundle([sgn1, sgn2])

    prev_balance = get_balance(tokens, currency, accounts[1])

    claim_contract.claim(currency, accounts[0].address, signatures.amounts,
                            signatures.v, signatures.r, signatures.s, {"from": accounts[1], "gas_price": 0})

    assert get_balance(tokens, currency, accounts[1]) == prev_balance + web3.toWei(3,'ether')

    sgn3 = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(3,'ether'), 3)
    sgn4 = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(2,'ether'), 4)
    sgn5 = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(1.5,'ether'), 5)
    sgn5b = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(1,'ether'), 5)

    prev_balance = get_balance(tokens, currency, accounts[1])

    signatures = sign_bundle([sgn3, sgn4, sgn5])
    
    with reverts("insuf balance"):
        claim_contract.claim(currency, accounts[0].address, signatures.amounts,
                            signatures.v, signatures.r, signatures.s,
                                {"from": accounts[1], "gas_price": 0})

    signatures = sign_bundle([sgn3, sgn4, sgn5b])
    claim_contract.claim(currency, accounts[0].address, signatures.amounts,
                            signatures.v, signatures.r, signatures.s,
                                {"from": accounts[1], "gas_price": 0})

    assert get_balance(tokens, currency, accounts[1]) == prev_balance + web3.toWei(6,'ether')

    # Any amount should fail since balance is empty
    sgn6 = sign_claim(accounts[0], accounts[1].address, currency, 1, 6)
    with reverts("insuf balance"):
        claim_contract.claim(currency, accounts[0].address, [1], [sgn6.v], [sgn6.r], [sgn6.s], {"from": accounts[1], "gas_price": 0})

    claim_contract.revoke(currency, web3.toWei(10,'ether'), {"from": accounts[2], "gas_price": 0})
    
    assert "10 ether" == get_balance(tokens, currency, accounts[2])
    assert 0 == get_balance(tokens, currency, claim_contract) """
