# Inverse Panopticon: Historical Verdict Snapshot

**Status: superseded by later measurements**  
**Date of original experiment: March 2026**

This file is retained to document an earlier interpretation produced during the investigation. It is **not** the current project conclusion.

## Original hypothesis

The experiment tested whether a TTL-limited FIN could alter an in-path observer's TCP state while the end-to-end connection remained usable.

An endpoint ACK observed after the TTL-limited FIN was initially interpreted as evidence that intermediary state had been evicted.

## Later result

Subsequent measurements did **not** support that interpretation.

`CONCLUDING_REPORT.md` records the later result as:

- the Ghost-FIN / `PhlegethonSink` hypothesis remained tracked under the tested conditions;
- continued endpoint connectivity does not prove that an intermediary discarded its state;
- a response from the destination is insufficient to establish what an unseen middlebox stored, parsed, or forgot.

Therefore the earlier claim of a verified DPI-state evasion is withdrawn.

## What remains useful

The experiment still demonstrates a useful methodological lesson:

> An endpoint-side success condition is not automatically a middlebox-state success condition.

To establish intermediary state transitions rigorously, a controlled testbed needs observation points before and after the middlebox, or another direct state oracle.

For the current interpretation of the March 2026 work, see:

- `CONCLUDING_REPORT.md`
- the repository-level `README.md`

This historical file is preserved so the evolution of the hypothesis remains visible rather than being silently rewritten.
