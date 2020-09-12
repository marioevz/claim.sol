// SPDX-License-Identifier: GNU

import "./IERC20.sol";
import "./SafeMath.sol";
import "./EthAddressLib.sol";

pragma solidity ^0.6.0;

contract Claim {
    using SafeMath for uint256;

    // Token -> Distributor -> Balance
    mapping (address => mapping (address => uint256)) public balances;
    // Token -> Distributor -> Claimer -> Nonce
    mapping (address => mapping (address => mapping (address => uint256))) public nonces;

    constructor()
    public { }

    receive()
    external payable
    {
        distribute(EthAddressLib.ethAddress(), msg.value);
    }

    function distribute(address token, uint256 amount)
    public payable
    returns (bool) 
    {
        return distribute(msg.sender, token, amount);
    }

    function distribute(address signer, address token, uint256 amount)
    public payable
    returns (bool) 
    {
        if (token == EthAddressLib.ethAddress()) {
            require (msg.value == amount);
        } else {
            require (IERC20(token).transferFrom(msg.sender, address(this), amount));
        }
        balances[token][signer] = balances[token][signer].add(amount);
        return true;
    }

    function revoke(address token, uint256 amount)
    public
    returns (bool) 
    {
        require (amount > 0);
        require (balances[token][msg.sender] >= amount);
        balances[token][msg.sender] = balances[token][msg.sender].sub(amount);
        if (token == EthAddressLib.ethAddress()) {
            require (msg.sender.send(amount));
        } else {
            require (IERC20(token).transfer(msg.sender, amount));
        }
        return true;
    }

    function claim(address token, address distributor, uint256[] calldata amounts, uint8[] calldata _v, bytes32[] calldata _r, bytes32[] calldata _s)
    external
    returns (bool) 
    {
        require (amounts.length > 0);
        require ((amounts.length == _v.length) &&
                 (_v.length == _r.length) &&
                 (_r.length == _s.length));
        uint256 currentAmount = 0;
        uint256 currentNonce = nonces[token][distributor][msg.sender];
        for (uint256 i = 0; i < amounts.length; i++) {
            // bytes32 message = keccak256(abi.encodePacked(msg.sender, token, amounts[i], currentNonce));
            require (distributor == ecrecover(keccak256(abi.encodePacked(msg.sender, token, amounts[i], currentNonce)), _v[i], _r[i], _s[i]));
            currentAmount = currentAmount.add(amounts[i]);
            currentNonce++;
        }
        
        require (currentAmount > 0);
        require (balances[token][distributor] >= currentAmount);

        balances[token][distributor] = balances[token][distributor].sub(currentAmount);
        nonces[token][distributor][msg.sender] = currentNonce;

        if (token == EthAddressLib.ethAddress()) {
            require (msg.sender.send(currentAmount));
        } else {
            require (IERC20(token).transfer(msg.sender, currentAmount));
        }
        return true;
    }

}