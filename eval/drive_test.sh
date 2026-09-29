#!/usr/bin/env bash
# Drives the reduced test runs and learning curves across quota days (CLAUDE.md "Quota rules"): for each job in
# order, wait until Groq has enough tokens, resume it, and repeat until all 24 cases are done. Jobs: arms C, D,
# A, B (eval/run_arms.py) and RH, RV, the Hindsight and vector replays (eval/replay.py). Run ID test1 for all.
# A lock directory stops a second driver from running the same jobs at once. Never reads ground truth itself;
# per-case predictions stay out of the log.
# Usage: bash eval/drive_test.sh [JOBS...]   (default: C D RH RV A B)
set -u
cd "$(dirname "$0")/.."
LOCK=data/runs/drive_test.lock
mkdir -p data/runs
if ! mkdir "$LOCK" 2>/dev/null; then echo "another driver holds $LOCK; stop it or remove the lock"; exit 1; fi
trap 'rmdir "$LOCK"' EXIT
PY=.venv/Scripts/python
IDS=$($PY -c "import json;d=json.load(open('data/cases/test_reduced.json'));print(','.join(sorted(i for g in d['groups'].values() for i in g)))")
N=$(echo "$IDS" | tr ',' '\n' | wc -l)
WANT=30000   # tokens to have before a resume, so each attempt does several cases
left() { $PY -c "from api.llm import LLM;print(LLM().limiter.tokens_remaining_today('openai/gpt-oss-120b') or 0)" 2>/dev/null | tail -1; }
done_n() {
  case "$1" in
    RH|RV) f="eval/results/replay-$([ "$1" = RH ] && echo hindsight || echo vector)-test-test1.json"
           $PY -c "import json,pathlib;p=pathlib.Path('$f');print(len(json.loads(p.read_text(encoding='utf-8'))['rows']) if p.exists() else 0)";;
    *)     $PY -c "
import json,pathlib;p=pathlib.Path('eval/results/run-bench-test-$1-test1.json')
print(len({r['case_id'] for r in json.loads(p.read_text(encoding='utf-8'))['rows'] if r['arm']=='$1'}) if p.exists() else 0)";;
  esac
}
run_job() {
  case "$1" in
    RH) $PY -m eval.replay --backend hindsight --split test --run test1 --resume --force 2>&1 | grep -v "^[A-E] TEST-";;
    RV) $PY -m eval.replay --backend vector --split test --run test1 --resume --force 2>&1 | grep -v "^[A-E] TEST-";;
    *)  $PY -m eval.run_arms --arm "$1" --dataset bench --split test --only "$IDS" --run test1 --resume --force 2>&1 \
          | grep -v "^[A-E] TEST-";;
  esac
}
JOBS=("$@"); [ ${#JOBS[@]} -eq 0 ] && JOBS=(C D RH RV A B)
for JOB in "${JOBS[@]}"; do
  for attempt in $(seq 1 40); do
    d=$(done_n "$JOB"); [ "$d" -ge "$N" ] && break
    while [ "$(left)" -lt "$WANT" ]; do sleep 900; done
    echo "$(date -u +%FT%TZ) $JOB: $d of $N done, resuming (attempt $attempt)"
    run_job "$JOB"
  done
  echo "$(date -u +%FT%TZ) $JOB: $(done_n "$JOB") of $N done"
done
