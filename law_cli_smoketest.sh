#!/usr/bin/env bash
set -euo pipefail

LOG="law_cli_smoketest.log"
: > "$LOG"

h() { echo -e "\n========================================\n$*\n========================================"; }
run() {
  echo -e "\n\$ $*" | tee -a "$LOG"
  "$@" 2>&1 | tee -a "$LOG"
}

h "1) Create sample incidents"
OUT1=$(python3 main.py law report "Alice bumped into Bob near the line" --party=Alice --party=Bob --kind=physical --severity=low || true)
echo "$OUT1" | tee -a "$LOG"
ID1=$(echo "$OUT1" | sed -n 's/.*[Ii][Dd][^0-9]*\([0-9]\+\).*/\1/p' | tail -n1 || true)

OUT2=$(python3 main.py law report "Bob pushed Charlie" --party=Bob --party=Charlie --kind=physical --severity=high || true)
echo "$OUT2" | tee -a "$LOG"
ID2=$(echo "$OUT2" | sed -n 's/.*[Ii][Dd][^0-9]*\([0-9]\+\).*/\1/p' | tail -n1 || true)

# Fallback if IDs couldn't be parsed
if [[ -z "${ID1:-}" || -z "${ID2:-}" ]]; then
  echo "(!) Could not parse IDs from output. Falling back to 1 and 2." | tee -a "$LOG"
  ID1="${ID1:-1}"
  ID2="${ID2:-2}"
fi

echo "Using IDs: ID1=$ID1  ID2=$ID2" | tee -a "$LOG"

h "2) Tag / Assign / Evidence"
run python3 main.py law tag "$ID1" hallway
run python3 main.py law assign "$ID2" Mediator_Jane
run python3 main.py law evidence add "$ID2" "Camera footage clip id=CF-8831"
run python3 main.py law evidence list "$ID2"

h "3) Status / Severity updates"
run python3 main.py law set-status "$ID2" resolved
run python3 main.py law set-severity "$ID1" medium

h "4) Finder queries"
run python3 main.py law find --kw=pushed
run python3 main.py law find --status=open
run python3 main.py law find --tag=hallway --json
run python3 main.py law find --party=Alice --kind=physical

h "Done"
echo "Log saved to: $LOG"
