// SPDX-License-Identifier: GNU

import "../interfaces/IERC20.sol";
import "../libraries/SafeMath.sol";
import "../libraries/EthAddressLib.sol";

pragma solidity ^0.6.0;

contract Claim {
    using SafeMath for uint256;

    // Token -> Distributor -> Balance
    mapping (address => mapping (address => uint256)) internal _balances;
    // Token -> Distributor -> Claimer -> Nonce
    mapping (address => mapping (address => mapping (address => uint256))) internal _nonces;

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

    function check_transfer_amount(address token, uint256 amount)
    internal
    returns (bool)
    {
        if (token == EthAddressLib.ethAddress()) {
            return msg.value == amount;
        } else {
            return IERC20(token).transferFrom(msg.sender, address(this), amount);
        }
    }

    function distribute(address signer, address token, uint256 amount)
    public payable
    returns (bool) 
    {
        require (check_transfer_amount(token, amount));
        _balances[token][signer] = _balances[token][signer].add(amount);
        return true;
    }

    function revoke(address token, uint256 amount)
    public
    returns (bool) 
    {
        return _revoke(msg.sender, token, amount);
    }

    function revokeAll(address token)
    public
    returns (bool)
    {
        return _revoke(msg.sender, token, _balances[token][msg.sender]);
    }

    function _revoke(address payable distributor, address token, uint256 amount)
    internal
    returns (bool)
    {
        require (amount > 0);
        require (_balances[token][distributor] >= amount);
        _balances[token][distributor] = _balances[token][distributor].sub(amount);
        if (token == EthAddressLib.ethAddress()) {
            require (distributor.send(amount));
        } else {
            require (IERC20(token).transfer(distributor, amount));
        }
        return true;
    }

    function claim(address token, address distributor, uint256[] calldata amounts, uint8[] calldata _v, bytes32[] calldata _r, bytes32[] calldata _s)
    external
    returns (uint256 returnAmount) 
    {
        require ((amounts.length > 0) &&
                 (amounts.length == _v.length) &&
                 (_v.length == _r.length) &&
                 (_r.length == _s.length), "invalid inputs");
        returnAmount = 0;
        uint256 currentNonce = _nonces[token][distributor][msg.sender];
        
        for (uint256 i = 0; i < amounts.length; i++) {
            bytes32 message = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n104", msg.sender, token, amounts[i], currentNonce));
            require (distributor == ecrecover(message, _v[i], _r[i], _s[i]), "invalid signature");
            returnAmount = returnAmount.add(amounts[i]);
            currentNonce++;
        }
        
        require (returnAmount > 0, "zero amount");
        require (_balances[token][distributor] >= returnAmount, "insuf balance");

        _balances[token][distributor] = _balances[token][distributor].sub(returnAmount);
        _nonces[token][distributor][msg.sender] = currentNonce;

        if (token == EthAddressLib.ethAddress()) {
            require (msg.sender.send(returnAmount));
        } else {
            require (IERC20(token).transfer(msg.sender, returnAmount));
        }
    }

    function balanceOf(address distributor, address token)
    public
    returns (uint256)
    {
        return _balances[token][distributor];
    }

    function nonceOf(address distributor, address token, address receiver)
    public
    returns (uint256)
    {
        return _nonces[token][distributor][receiver];
    }

}