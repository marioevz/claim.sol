import pytest

from brownie import Claim, ERC20, accounts, web3, reverts
from utils import eth_address, int_to_hex, hex_pack, get_balance, sign_info, sign_claim, sign_bundle

@pytest.fixture
def claim_contract():
    return accounts[0].deploy(Claim)

@pytest.fixture
def tokens():
    t1 = ERC20.deploy("Test Token 1", "TST", {'from': accounts[0]})
    t2 = ERC20.deploy("Test Token 2", "TST", {'from': accounts[0]})
    t1.mint(accounts[0].address, web3.toWei(10,'ether'), {'from': accounts[0]})
    t1.mint(accounts[2].address, web3.toWei(10,'ether'), {'from': accounts[0]})
    t2.mint(accounts[1].address, web3.toWei(10,'ether'), {'from': accounts[0]})
    return {t1.address: t1, t2.address: t2}

@pytest.mark.parametrize('currency', [eth_address, 0])
def test_distribute_ether(claim_contract, tokens, currency):

    if currency != eth_address:
        currency = list(tokens.keys())[currency]

    if currency == eth_address:
        accounts[0].transfer(claim_contract.address, "10 ether", gas_price=0)
        accounts[2].transfer(claim_contract.address, "10 ether", gas_price=0)
        # Burn the rest
        accounts[0].transfer("0x0000000000000000000000000000000000000000", "90 ether", gas_price=0)
        accounts[2].transfer("0x0000000000000000000000000000000000000000", "90 ether", gas_price=0)
    else:
        tokens[currency].approve(claim_contract.address, web3.toWei(10,'ether'), {"from": accounts[0]})
        claim_contract.distribute(currency, web3.toWei(10,'ether'), {"from": accounts[0]})
        tokens[currency].approve(claim_contract.address, web3.toWei(10,'ether'), {"from": accounts[2]})
        claim_contract.distribute(currency, web3.toWei(10,'ether'), {"from": accounts[2]})

    assert "20 ether" == get_balance(tokens, currency, claim_contract)

    sgn0 = sign_claim(accounts[0], accounts[1].address, currency, web3.toWei(1,'ether'), 0)

    recovered = web3.eth.account.recoverHash(sgn0.h, sgn0.vrs)

    assert recovered == accounts[0].address

    prev_balance = get_balance(tokens, currency, accounts[1])

    claim_contract.claim(currency, accounts[0].address, [web3.toWei(1,'ether')], [sgn0.v], [sgn0.r], [sgn0.s], {"from": accounts[1], "gas_price": 0})

    assert get_balance(tokens, currency, accounts[1]) == prev_balance + web3.toWei(1,'ether')

    with reverts("invalid signature"):
        # Try to reuse signature, signature will fail due to the nonce chaning
        claim_contract.claim(currency, accounts[0].address, [web3.toWei(1,'ether')], [sgn0.v], [sgn0.r], [sgn0.s], {"from": accounts[1], "gas_price": 0})

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
    assert 0 == get_balance(tokens, currency, claim_contract)
