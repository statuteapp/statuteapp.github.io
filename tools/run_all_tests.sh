#!/usr/bin/env bash
# Runs every test in tools/ against an index.html (default: the one in the repository root). Exit code 0 only if everything passes.
#
# One-time setup (needs node 18+ and python3):
#     mkdir -p /tmp/tt && cd /tmp/tt && npm install jsdom leaflet@1.9.4
# Run:
#     NODE_PATH=/tmp/tt/node_modules bash tools/run_all_tests.sh [path/to/index.html] [path/to/fsa_places.json]
#
# To test an edit before pushing it: copy index.html to a temporary folder, run `python apply_patches.py` and each patches/*.py there
# (patches/README.md explains the rules), then pass that patched file here. Run the patches three times: the second and third runs
# must change nothing.
set -u
cd "$(dirname "$0")/.."
HTML="${1:-index.html}"; FSA="${2:-fsa_places.json}"; fail=0; out=$(mktemp)
for t in tools/test_*.py; do
  if timeout 300 python3 "$t" >"$out" 2>&1; then echo "PASS  $t"; else echo "FAIL  $t"; tail -8 "$out"; fail=1; fi
done
for t in tools/test_*.js; do
  if timeout 300 node "$t" "$HTML" "$FSA" >"$out" 2>&1; then echo "PASS  $t"; else echo "FAIL  $t"; grep -E "^(FAIL|TypeError|ReferenceError)" "$out" | head -8; fail=1; fi
done
if [ -f worker/test/receiver.test.mjs ]; then
  if timeout 300 node --test worker/test/*.test.mjs >"$out" 2>&1; then echo "PASS  worker/test (receiver)"; else echo "FAIL  worker/test (receiver)"; tail -8 "$out"; fail=1; fi
fi
rm -f "$out"
[ "$fail" = 0 ] && echo "ALL SUITES PASSED" || echo "SOME SUITES FAILED"
exit "$fail"
