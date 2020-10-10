import pytest
from brownie import MerkleClaim, ERC20, accounts, web3, reverts
from merkle import MerkleTree
from utils import eth_address, int_to_hex, hex_pack, get_balance

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
    eth_address,
    0])
def test_distribute_ether(claim_contract, tokens, currency):

    if currency != eth_address:
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

    if currency == eth_address:
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

    claim_contract.claim(currency, accounts[1].address, distributeTree.root, distributeTree.get_proof_by_idx(0), 0, web3.toWei(1,'ether'), {"from": accounts[1], "gas_price": 0})

    assert get_balance(tokens, currency, accounts[1]) == prev_balance + web3.toWei(1,'ether')
    

    with reverts("already claimed"):
        # Try to reuse proof, will fail due to the bitmap check
        claim_contract.claim(currency, accounts[1].address, distributeTree.root, distributeTree.get_proof_by_idx(0), 0, web3.toWei(1,'ether'), {"from": accounts[1], "gas_price": 0})

    with reverts("invalid proof"):
        # Try to claim with proper amount and index but invalid address, hence invalid proof
        claim_contract.claim(currency, accounts[1].address, distributeTree.root, distributeTree.get_proof_by_idx(1), 1, web3.toWei(2,'ether'), {"from": accounts[1], "gas_price": 0})

    # Correctly claim with following index
    prev_balance = get_balance(tokens, currency, accounts[2])
    claim_contract.claim(currency, accounts[2].address, distributeTree.root, distributeTree.get_proof_by_idx(1), 1, web3.toWei(2,'ether'), {"from": accounts[2], "gas_price": 0})
    assert get_balance(tokens, currency, accounts[2]) == prev_balance + web3.toWei(2,'ether')

    # Correctly claim with index out of order
    prev_balance = get_balance(tokens, currency, accounts[4])
    claim_contract.claim(currency, accounts[4].address, distributeTree.root, distributeTree.get_proof_by_idx(3), 3, web3.toWei(4,'ether'), {"from": accounts[4], "gas_price": 0})
    assert get_balance(tokens, currency, accounts[4]) == prev_balance + web3.toWei(4,'ether')

    # Correctly claim remaining index with other account
    prev_balance = get_balance(tokens, currency, accounts[3])
    claim_contract.claim(currency, accounts[3].address, distributeTree.root, distributeTree.get_proof_by_idx(2), 2, web3.toWei(3,'ether'), {"from": accounts[1], "gas_price": 0})
    assert get_balance(tokens, currency, accounts[3]) == prev_balance + web3.toWei(3,'ether')