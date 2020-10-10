import web3
Web3 = web3.Web3()

eth_address = '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'

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
    if currency == eth_address:
        return account.balance()
    else:
        return tokens[currency].balanceOf(account.address)

def sign_info(signature):
    sgn = signature.hex()[2:]
    r = '0x' + sgn[0:64]
    s = '0x' + sgn[64:128]
    ex = 27
    v = hex(int(sgn[128:130], 16) + ex)
    return {"r": r, "s":s, "v":v}

def sign_claim(account, to, token, amount, nonce):
    message = hex_pack(to, token, amount, nonce)
    sgn = sign_info(Web3.eth.sign(account.address, hexstr=message))
    message = '0x' + ("\x19Ethereum Signed Message:\n" + str(int((len(message) - 2) / 2))).encode('ascii').hex() + message[2:]
    h = Web3.keccak(hexstr=message).hex()
    return type('Signature', (object,),
                            {   "message": message,
                                "h": h, "to":to, "token":token, "amount":amount,
                                "r": sgn["r"], "s":sgn["s"], "v":sgn["v"],
                                "vrs": (sgn["v"],sgn["r"],sgn["s"])
                            })

def sign_bundle(signatures):
    return type('Signatures', (object,),
        {"amounts": [x.amount for x in signatures],
            "v": [x.v for x in signatures],
            "r": [x.r for x in signatures],
            "s": [x.s for x in signatures]})