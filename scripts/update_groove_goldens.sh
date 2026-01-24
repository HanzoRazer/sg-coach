#!/usr/bin/env bash
# scripts/update_groove_goldens.sh
# Update groove golden vectors with changelog entry
#
# Usage:
#   ./scripts/update_groove_goldens.sh "reason for update"
#
set -euo pipefail

python -m sg_coach.groove_replay_gate_v1 fixtures/golden/groove_vectors \
  --update-golden \
  --bump-changelog "${1:-accept updated intent mapping}"
