// SPDX-License-Identifier: GNU

import "../interfaces/IERC20.sol";
import "../libraries/SafeMath.sol";
import "../libraries/MerkleProof.sol";
import "../libraries/EthAddressLib.sol";

pragma solidity ^0.6.0;
pragma experimental ABIEncoderV2;

contract MerkleClaim {
    using SafeMath for uint256;

    // Token -> MerkleRoot -> Balance
    mapping (address => mapping (bytes32 => uint256)) internal _balances;
    // Token -> MerkleRoot -> Index Word -> Claimed Bitmap
    mapping (address => mapping (bytes32 => mapping(uint256 => uint256))) internal _bitmaps;

    constructor()
    public { }

    receive()
    external payable
    {
        require(false); // We can't distribute to a null merkle root
        // distribute(EthAddressLib.ethAddress(), msg.value);
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

    function transfer_amount(address payable toSend, address token, uint256 amount)
    internal
    returns (bool)
    {
        if (token == EthAddressLib.ethAddress()) {
            require (toSend.send(amount));
        } else {
            require (IERC20(token).transfer(toSend, amount));
        }
    }

    // If you add tokens to an invalid merkle-root, the funds will be forever lost.
    // There is no way to check whether a merkle-tree has already been used:
    // Balance will only tell that the root has no funds at the moment, but will not tell if the
    // tree was emptied.
    // We could check the bitmaps but would be exhaustive.
    function distribute(address token, bytes32 merkleRoot, uint256 amount)
    public payable
    returns (bool) 
    {
        require(merkleRoot != 0);
        require (check_transfer_amount(token, amount));
        _balances[token][merkleRoot] = _balances[token][merkleRoot].add(amount);
        return true;
    }

    function _checkClaim (
        address token,
        bytes32 merkleRoot,
        bytes32[] memory merkleProof,
        uint256 index,
        address account,
        uint256 amount
    )
    private
    {
        require(merkleProof.length > 0, "proof length");
        require (!isClaimed(token, merkleRoot, index), "already claimed");
        require (_balances[token][merkleRoot] >= amount, "insufficient balance");
        bytes32 leaf = keccak256(abi.encodePacked(index, account, amount));
        require (MerkleProof.verify(merkleProof, merkleRoot, leaf), "invalid proof");
        _balances[token][merkleRoot] = _balances[token][merkleRoot].sub(amount);
        _setClaimed(token, merkleRoot, index);
    }

    function claim (
        address token,
        address payable account,
        bytes32 merkleRoot,
        bytes32[] calldata merkleProof,
        uint256 index,
        uint256 amount
    )
    external
    {
        require (amount > 0);
        _checkClaim(token, merkleRoot, merkleProof, index, account, amount);
        transfer_amount(account, token, amount);
    }

    function multiClaim (
        address token,
        address payable account,
        bytes32[] calldata merkleRoots,
        bytes32[][] calldata merkleProofs,
        uint256[] calldata indexes,
        uint256[] calldata amounts
    )
    external
    returns (uint256 returnAmount)
    {
        require(merkleProofs.length == indexes.length
                && merkleProofs.length == amounts.length
                && merkleProofs.length == merkleRoots.length, 'Inv params');
        returnAmount = 0;
        for(uint256 i = 0; i < merkleProofs.length; i++)  {
            _checkClaim(token, merkleRoots[i], merkleProofs[i], indexes[i], account, amounts[i]);
            returnAmount = returnAmount.add(amounts[i]);
        }
        require (returnAmount > 0);
        transfer_amount(account, token, returnAmount);
    }

    function balanceOf(address token, bytes32 merkleRoot)
    public
    returns (uint256)
    {
        return _balances[token][merkleRoot];
    }

    function isClaimed(address token, bytes32 merkleRoot, uint256 index)
    public
    returns (bool)
    {
        uint256 word = _bitmaps[token][merkleRoot][index / 256];
        uint256 mask = 1 << (index % 256);
        return (mask & word) == mask;
    }

    function _setClaimed(address token, bytes32 merkleRoot, uint256 index)
    private
    {
        uint256 mask = 1 << (index % 256);
        _bitmaps[token][merkleRoot][index / 256] = _bitmaps[token][merkleRoot][index / 256] | mask;
    }

}