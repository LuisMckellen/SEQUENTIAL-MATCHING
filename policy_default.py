"""Local stand-in for the container entrypoint: runs `python policy.py` with no arguments (our method).
evaluate.py always forwards `--baseline <name>` in trusted local mode, so use:
    python evaluate.py --policy policy_default.py --seeds ... --variants all --output results/method.json
"""
import sys

from policy import main

if __name__ == "__main__":
    raise SystemExit(main([]))
