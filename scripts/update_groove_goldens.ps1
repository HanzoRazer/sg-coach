# scripts/update_groove_goldens.ps1
# Update groove golden vectors with changelog entry
#
# Usage:
#   .\scripts\update_groove_goldens.ps1 "reason for update"
#
param(
    [string]$Reason = "accept updated intent mapping"
)

$ErrorActionPreference = "Stop"

python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors `
    --update-golden `
    --bump-changelog $Reason
