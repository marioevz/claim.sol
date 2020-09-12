// SPDX-License-Identifier: GNU

import "./IERC20.sol";
import "./SafeMath.sol";
import "./EthAddressLib.sol";

pragma solidity ^0.7.0;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

contract Claim {
    using SafeMath for uint256;

    // Token -> Distributor -> Balance
    mapping (address => mapping (address => uint256)) public balances;
    // Token -> Distributor -> Claimer -> Nonce
    mapping (address => mapping (address => mapping (address => uint256))) public nonces;

    constructor() { }

    receive()
    external payable
    {
        distribute(EthAddressLib.ethAddress(), msg.value);
    }

    function distribute(address token, uint256 amount)
    public payable
    returns (bool success) 
    {
        if (token == EthAddressLib.ethAddress()) {
            require (msg.value == amount);
        } else {
            require (IERC20(token).transferFrom(msg.sender, address(this), amount));
        }
        balances[token][msg.sender] = balances[token][msg.sender].add(amount);
        return true;
    }

    function claim(address token, address distributor, uint256[] amounts, uint8[] _v, bytes32[] _r, bytes32[] _s)
    external
    returns (bool success) 
    {
        address claimer = msg.sender;
        require (amounts.length > 0);
        require ((amounts.length == _v.length) &&
                 (_v.length == _r.length) &&
                 (_r.length == _s.length));
        uint256 currentAmount = 0;
        uint256 currentNonce = nonces[token][distributor][claimer];
        for (uint256 i = 0; i < amounts.length; i++) {
            bytes32 message = keccak256(abi.encodePacked(claimer, token, amounts[i], currentNonce));
            require (distributor == ecrecover(message, _v[i], _r[i], _s[i]));
            currentAmount = currentAmount.add(amounts[i]);
            currentNonce++;
        }
        
        require (currentAmount > 0);
        require (balances[token][distributor] >= currentAmount);

        balances[token][distributor] = balances[token][distributor].sub(currentAmount);
        nonces[token][distributor][claimer] = currentNonce;

        if (token == EthAddressLib.ethAddress()) {
            require (claimer.send(currentAmount));
        } else {
            require (IERC20(token).transfer(claimer, currentAmount));
        }
        return true;
    }

}