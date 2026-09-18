// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

/// @title AgentWitnessRegistry
/// @notice One-event/one-claim trust rail for concurrent AI agents.
/// @dev Private payloads MUST stay off-chain. eventKey, intentHash and outcome
///      hashes are content digests computed by the versioned off-chain schema.
contract AgentWitnessRegistry {
    enum Outcome {
        None,
        Completed,
        Rejected,
        OutcomeUnknown,
        Held
    }

    enum Resolution {
        None,
        Completed,
        Rejected,
        Held
    }

    struct ClaimRecord {
        address claimant;
        bytes32 intentHash;
        Outcome outcome;
        bytes32 outcomeHash;
        Resolution resolution;
        bytes32 resolutionHash;
        uint64 claimedAtBlock;
        uint64 finalizedAtBlock;
        uint64 reconciledAtBlock;
    }

    error ZeroValue();
    error AlreadyClaimed(bytes32 eventKey, address claimant);
    error NotClaimed(bytes32 eventKey);
    error NotClaimant(bytes32 eventKey, address expected, address actual);
    error InvalidOutcome();
    error AlreadyFinalized(bytes32 eventKey);
    error NotReconcilable(bytes32 eventKey);

    mapping(bytes32 => ClaimRecord) private _claims;

    event ClaimRecorded(
        bytes32 indexed eventKey,
        address indexed claimant,
        bytes32 indexed intentHash,
        uint64 blockNumber
    );
    event OutcomeRecorded(
        bytes32 indexed eventKey,
        address indexed claimant,
        Outcome outcome,
        bytes32 indexed outcomeHash,
        uint64 blockNumber
    );
    event OutcomeReconciled(
        bytes32 indexed eventKey,
        address indexed claimant,
        Resolution resolution,
        bytes32 indexed resolutionHash,
        uint64 blockNumber
    );

    /// @notice Atomically claim one triggering event.
    /// @dev Different workers or drafts cannot bypass the global eventKey slot.
    function claim(bytes32 eventKey, bytes32 intentHash) external {
        if (eventKey == bytes32(0) || intentHash == bytes32(0)) revert ZeroValue();
        ClaimRecord storage record = _claims[eventKey];
        if (record.claimant != address(0)) {
            revert AlreadyClaimed(eventKey, record.claimant);
        }
        record.claimant = msg.sender;
        record.intentHash = intentHash;
        record.claimedAtBlock = _blockNumber64();
        emit ClaimRecorded(eventKey, msg.sender, intentHash, record.claimedAtBlock);
    }

    /// @notice Finalize the first observed provider/side-effect outcome exactly once.
    function finalize(bytes32 eventKey, Outcome outcome, bytes32 outcomeHash) external {
        ClaimRecord storage record = _requireClaimant(eventKey);
        if (record.outcome != Outcome.None) revert AlreadyFinalized(eventKey);
        if (
            outcome != Outcome.Completed &&
            outcome != Outcome.Rejected &&
            outcome != Outcome.OutcomeUnknown &&
            outcome != Outcome.Held
        ) revert InvalidOutcome();
        if (outcomeHash == bytes32(0)) revert ZeroValue();

        record.outcome = outcome;
        record.outcomeHash = outcomeHash;
        record.finalizedAtBlock = _blockNumber64();
        emit OutcomeRecorded(eventKey, msg.sender, outcome, outcomeHash, record.finalizedAtBlock);
    }

    /// @notice Resolve an explicitly unknown first outcome after authoritative reconciliation.
    /// @dev This is the only permitted second outcome transition.
    function reconcile(bytes32 eventKey, Resolution resolution, bytes32 resolutionHash) external {
        ClaimRecord storage record = _requireClaimant(eventKey);
        if (
            record.outcome != Outcome.OutcomeUnknown ||
            record.resolution != Resolution.None
        ) revert NotReconcilable(eventKey);
        if (
            resolution != Resolution.Completed &&
            resolution != Resolution.Rejected &&
            resolution != Resolution.Held
        ) revert InvalidOutcome();
        if (resolutionHash == bytes32(0)) revert ZeroValue();

        record.resolution = resolution;
        record.resolutionHash = resolutionHash;
        record.reconciledAtBlock = _blockNumber64();
        emit OutcomeReconciled(eventKey, msg.sender, resolution, resolutionHash, record.reconciledAtBlock);
    }

    function getClaim(bytes32 eventKey) external view returns (ClaimRecord memory) {
        return _claims[eventKey];
    }

    function isClaimed(bytes32 eventKey) external view returns (bool) {
        return _claims[eventKey].claimant != address(0);
    }

    function _requireClaimant(bytes32 eventKey) private view returns (ClaimRecord storage record) {
        record = _claims[eventKey];
        if (record.claimant == address(0)) revert NotClaimed(eventKey);
        if (record.claimant != msg.sender) {
            revert NotClaimant(eventKey, record.claimant, msg.sender);
        }
    }

    function _blockNumber64() private view returns (uint64) {
        if (block.number > type(uint64).max) revert();
        return uint64(block.number);
    }
}
