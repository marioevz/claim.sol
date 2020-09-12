# claim.sol
A smart contract that enables distribution of tokens 

There has not been any formal audit on this code, use at your own risk.

Steps to use:

Call approve on the token's contract with this contract as spender.

Call distribute function with the token address (0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE for Ether) and the amount to distribute.

Sign and distribute the signatures to each recipient of the distribution, how this is done is up to you.

Signature must contain the following information:
 - Address to which I am distributing
 - Token I am distributing
 - Amount I am distributing to this address
 - How many times have I distributed before to this address (nonce)
 
 Claimer must call claim function with the token to claim, the address that distributed the token, the amount(s) and the signature(s)
 
 Distributions can be done in batches, and claimers can accumulate signatures to claim multiple batches in a single transaction.
