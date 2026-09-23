---
status: partial
phase: 08-supply-chain-hardening
source: [08-VERIFICATION.md]
started: 2026-09-23T16:05:00Z
updated: 2026-09-23T16:05:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. CUDA lock installs on real hardware (requirements-cuda.txt)
expected: `pip install --require-hashes -r requirements-cuda.txt` exits 0 with no hash mismatch, and `torch.__version__` is exactly `2.14.0+cu130` (`torch.cuda.is_available()` is `True` on an NVIDIA+CUDA machine, `False` acceptable for install verification)
result: [approved by operator; torch.cuda.is_available() value not captured]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
- The operator approved the CUDA checkpoint but did not record the `torch.cuda.is_available()` value. The install itself is attested; a machine-captured value (e.g. `2.14.0+cu130 True`) would close this item.
