import pytest
from merkle import MerkleTree
from brownie import MerkleClaim, ERC20, accounts, web3, reverts
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
def test_distribute_multi_claim(claim_contract, tokens, currency):

    if currency != eth_address:
        currency = list(tokens.keys())[currency]

    distributeTree1 = MerkleTree([
        [
            {
                'type':'address',
                'value': accounts[1].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(0.5,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[2].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(1,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[3].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(1.5,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[4].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(2,'ether')
            }
        ],
    ])

    distributeTree2 = MerkleTree([
        [
            {
                'type':'address',
                'value': accounts[1].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(2,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[2].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(1.5,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[3].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(1,'ether')
            }
        ],
        [
            {
                'type':'address',
                'value': accounts[4].address
            },
            {
                'type':'uint256',
                'value': web3.toWei(0.5,'ether')
            }
        ],
    ])

    if currency == eth_address:
        claim_contract.distribute(currency, distributeTree1.root, web3.toWei(5,'ether'), {"from": accounts[0], "value": web3.toWei(5,'ether')})
        claim_contract.distribute(currency, distributeTree2.root, web3.toWei(5,'ether'), {"from": accounts[0], "value": web3.toWei(5,'ether')})
        #accounts[0].transfer(claim_contract.address, "10 ether", gas_price=0)
        #accounts[2].transfer(claim_contract.address, "10 ether", gas_price=0)
        # Burn the rest
        #accounts[0].transfer("0x0000000000000000000000000000000000000000", "90 ether", gas_price=0)
        #accounts[2].transfer("0x0000000000000000000000000000000000000000", "90 ether", gas_price=0)
    else:
        tokens[currency].approve(claim_contract.address, web3.toWei(10,'ether'), {"from": accounts[0]})
        claim_contract.distribute(currency, distributeTree1.root, web3.toWei(5,'ether'), {"from": accounts[0]})
        claim_contract.distribute(currency, distributeTree2.root, web3.toWei(5,'ether'), {"from": accounts[0]})

    assert "10 ether" == get_balance(tokens, currency, claim_contract)
    
    prev_balance = get_balance(tokens, currency, accounts[1])

    claim_contract.multiClaim(currency, accounts[1].address, [distributeTree1.root, distributeTree2.root], [distributeTree1.get_proof_by_idx(0), distributeTree2.get_proof_by_idx(0)], [0, 0], [web3.toWei(0.5,'ether'), web3.toWei(2,'ether')], {"from": accounts[1], "gas_price": 0})

    assert get_balance(tokens, currency, accounts[1]) == prev_balance + web3.toWei(2.5,'ether')
    