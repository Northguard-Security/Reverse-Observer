# Reverse Observer

**Experimental network-path and middlebox behavior measurement laboratory.**

Reverse Observer is a single-developer research repository for studying how stateful network intermediaries react to unusual but controlled packet sequences.

The main project lives under:

```text
RedTeam-Lab/InversePanopticon/
```

It contains experiments around:

- route and hop discovery;
- TTL-limited probing;
- RDAP-based network-registration context;
- TCP reset timing;
- structured and unstructured TLS-like trigger comparison;
- delayed and out-of-order TCP state behavior;
- checksum and reassembly behavior;
- fragmentation and sequence-space edge cases;
- protocol-dependent differences between TCP and UDP;
- preservation of hypotheses that were falsified, unsupported, or structurally invalid.

The repository is best understood as a **research notebook implemented with raw-packet tools**. It is not a production censorship detector, a verified DPI-vendor fingerprinting framework, a hardware-attribution system, or a general network-bypass product.

## Why “Reverse Observer”

The ordinary direction of observation is:

```text
middlebox -> observes endpoint traffic
```

This project reverses the question:

```text
endpoint experiment -> observes middlebox behavior
```

The objective is to vary protocol properties and inspect measurable responses without assuming that one explanation is uniquely correct.

The most useful outputs are often negative:

- a suspected shallow inspection window was not supported by later tests;
- several state-desynchronization hypotheses did not change the measured behavior;
- a TTL-limited FIN did not provide a valid oracle for intermediary state eviction;
- invalid checksums behaved differently from valid comparisons;
- some proposed constructions were invalid before any middlebox conclusion could be drawn;
- TCP and UDP produced different observable responses, but that difference did not by itself prove a QUIC bypass.

Preserving those corrections is a central part of the project.

## Current status

| Area | Current status |
|---|---|
| Raw route probing | Implemented |
| TTL sweeps and hop-local experiments | Implemented in several scripts |
| RDAP registration lookup | Implemented |
| TCP reset observation | Implemented |
| Structured TLS-like trigger tests | Implemented |
| State-persistence experiments | Implemented for selected cases |
| Fragmentation and sequence experiments | Implemented to varying depth |
| JSONL evidence logging | Present in parts of the suite |
| Repeatable local middlebox testbed | Not yet provided |
| Automated test suite | Not currently provided |
| Reproducible packet-capture corpus | Not currently included |
| Reliable DPI-vendor identification | Not established |
| Reliable hardware classification from timing | Not established |
| General censorship attribution | Not established |
| Universal evasion technique | Not established |
| Production readiness | Not claimed |

## Evidence vocabulary

### Observed

A response was recorded during a particular run, path, destination, time, and local network configuration.

Example:

> A TCP reset followed a selected stimulus during the recorded experiment.

### Inferred

An explanation is consistent with the observation but is not uniquely proven by it.

Example:

> A stateful intermediary may have inspected content carried in the flow.

### Falsified under tested conditions

A specific prediction did not occur in the implemented experiment.

This does not prove that every possible variant is impossible. It means the tested construction failed to produce its predicted result.

### Unverified

The code or theory exists, but the repository does not contain a sufficiently controlled feedback loop or evidence record to support the claim.

### Structurally invalid

The proposed mechanism conflicts with protocol or endpoint behavior before any middlebox-specific conclusion can be drawn.

These categories are more useful than labeling every outcome “success” or “failure.”

## What the March 2026 experiments measured

The concluding report summarizes experiments performed primarily on **March 1–2, 2026** against a measured path toward `torproject.org`.

During those runs, the repository recorded behavior consistent with:

- content-sensitive handling of selected TCP/443 stimuli;
- the selected trigger remaining observable beyond a very shallow byte offset;
- persistence of relevant behavior through delayed out-of-order TCP tests up to the tested 120-second range;
- checksum-aware differences;
- selected fragment and sequence-overlap constructions failing to suppress the measured trigger;
- different observable responses between selected TCP/443 and UDP/443 probes.

These findings are **path and time dependent**.

They do not establish that:

- every path to the same destination behaves identically;
- a destination or transit operator intentionally performed the observed behavior;
- a specific commercial DPI product was present;
- a particular router represented by traceroute generated a reset;
- the same policy remains active now;
- absence of a TCP-style reset on UDP proves successful QUIC connectivity;
- a protocol difference is a permanent or general bypass.

The narrow conclusion is:

> The recorded path exhibited repeatable, stateful, content-sensitive, and transport-dependent response behavior under the selected stimuli, while the exact implementation and response origin remained underdetermined.

## Attribution boundaries

### RDAP context

RDAP can identify the organization to which an address range is registered or delegated.

It does not identify which team, appliance, policy, tenant, subcontractor, or upstream system generated a packet.

### Route position

TTL-limited probes can suggest where a response becomes observable along one measured route.

ECMP, asymmetric routing, tunnels, MPLS, ICMP rate limiting, load balancing, and route changes can distort that picture.

### Response origin

Source address, TTL, timing, and quoted packet data can help form a hypothesis about where a response originated.

They do not automatically prove physical device identity.

### Vendor and hardware class

Earlier versions of `main.py` and `ShadowCaster.py` mapped small timing or ICMP-quotation differences directly to hardware classes and named vendors.

That mapping has been removed.

The current tools report descriptive timing and quotation observations instead. The collected data is not sufficient for reliable vendor or hardware identification.

## Repository layout

```text
Reverse-Observer/
├── README.md
└── RedTeam-Lab/
    └── InversePanopticon/
        ├── main.py
        ├── EntropyMask.py
        ├── TriggerValidator.py
        ├── ChronosShroud.py
        ├── ChecksumShadow.py
        ├── ShadowCaster.py
        ├── PhlegethonSink.py
        ├── GhostDeceptor.py
        ├── FinalVerdict.py
        ├── additional protocol experiments
        ├── AuditDossier.md
        ├── AuditDossier_Update.md
        ├── FinalAudit.md
        ├── FINAL_VERDICT.md
        ├── CrossTargetIntel.md
        ├── CONCLUDING_REPORT.md
        └── IntelligenceLedger.jsonl
```

Many filenames retain the theatrical names used during exploration. A filename does not indicate validated capability.

Obsolete model-control prompt files have been removed from the repository because they were not technical specifications, evidence, or reproducibility material.

## Main measurement tool

`RedTeam-Lab/InversePanopticon/main.py` combines:

1. TCP-based route probing;
2. RDAP registration context for observed addresses;
3. baseline ICMP timing samples;
4. a second timing sample around a historical TLS-like stimulus;
5. a descriptive timing-delta bucket.

Earlier versions labeled those buckets as software DPI, ASIC acceleration, or passive taps. Those labels were unsupported and have been removed.

Timing deltas can arise from many unrelated causes and must not be treated as hardware identification.

## ICMP quotation experiment

`ShadowCaster.py` compares selected fields from ICMP Time Exceeded quotations with the packet that was transmitted.

Earlier versions attempted to map those differences directly to Sandvine, Allot, Cisco, or Huawei products. The current implementation reports only the observed quotation differences.

Vendor attribution requires independent evidence.

## Endpoint ACK versus middlebox state

`PhlegethonSink.py` tests whether a destination ACK is observed after a TTL-limited FIN and subsequent payload.

The current output explicitly distinguishes:

```text
endpoint acknowledged data
```

from:

```text
intermediary discarded its state
```

The first can be observed by the tool. The second cannot be established without a direct middlebox-state oracle or controlled capture around the intermediary.

## Offset-response experiment

`FinalVerdict.py` retains the historical offset sweep, but no longer reports the first matching reset as an “inspection window.”

The historical implementation stops at the first tested offset associated with a matching RST. Therefore it cannot determine the upper boundary of an inspection window from that run.

## Historical reports

### `CONCLUDING_REPORT.md`

This is the current synthesis of the March 2026 measurements. Revision 4 deliberately separates observations from interpretations and withdraws the earlier “confirmed QUIC bypass” wording.

### `AuditDossier.md` and `AuditDossier_Update.md`

These preserve early timing observations but no longer assign hardware architecture or policy intent from small RTT samples.

### `FinalAudit.md`

This preserves the TCP/UDP comparison while explicitly stating that absence of a TCP-style reset on UDP is not proof of successful application-layer QUIC connectivity.

### `CrossTargetIntel.md`

This records the early cross-destination comparison and explicitly marks the shallow 32-byte window hypothesis as superseded by later experiments.

### `FINAL_VERDICT.md`

This is retained as a historical record of an interpretation that was later withdrawn. It now points readers to the later measurement result instead of asserting verified middlebox-state eviction.

### `IntelligenceLedger.jsonl`

Where available, raw chronological evidence is preferable to prose verdicts because it preserves the evolution of the hypotheses.

## Offline artifact integrity

A small **standard-library-only** helper, `tools/evidence_manifest.py`, creates an explicit SHA-256 manifest for files collected in an authorized, local experiment. It does **not** send traffic, collect packets, or infer which network component produced an observation.

From the directory containing the artifact paths:

```bash
python tools/evidence_manifest.py \
  --experiment controlled-path-001 \
  --artifact captures/control.pcap \
  --artifact captures/stimulus.pcap \
  --out run-manifest.json

python tools/evidence_manifest.py --verify run-manifest.json
```

The example presumes those two capture files already exist. The program refuses missing, non-regular, absolute, and outside-directory artifacts and will not overwrite an existing manifest. It stores each file's relative path, size, SHA-256, timestamp of manifest creation, and an **analyst-supplied**, explicitly non-validated hypothesis status. The default status is `unverified`.

A successful `--verify` checks whether the files still match their recorded bytes. It **does not establish source authenticity, capture completeness, clock accuracy, attribution, causal interpretation, or legal chain of custody**. The artifact schema covers integrity, not yet the full measurement-record fields listed below.

CI runs synthetic creation, tampering, and invalid-path checks completely offline. It does not execute the raw-packet research scripts or run against live middleboxes.

## Requirements

The scripts primarily use:

- Python 3.9 or newer;
- Scapy;
- raw-socket privileges;
- network access for RDAP queries in tools that perform registration lookup.

A minimal local installation is:

```bash
python -m pip install scapy
```

Raw-packet operations commonly require administrator or root privileges.

Do not grant elevated privileges to code that has not first been inspected. Several scripts intentionally construct malformed, overlapping, fragmented, out-of-order, TTL-limited, or state-stressing traffic.

## Preferred experimental setup

The strongest environment is an isolated testbed containing:

- a source host or network namespace;
- a controlled middlebox or proxy;
- a destination host owned by the researcher;
- packet capture on both sides of the middlebox;
- synchronized clocks where timing comparisons matter;
- a clean baseline before each stimulus;
- explicit rate limits.

```text
source namespace -> controlled middlebox -> destination namespace
```

This makes it possible to distinguish:

- what the sender transmitted;
- what the intermediary received;
- what the intermediary forwarded;
- what the destination reconstructed;
- which component generated each response.

Without those observation points, many conclusions remain underdetermined.

## Measurement discipline

For each experiment, record at least:

```text
experiment ID
UTC timestamp
source environment
resolved destination addresses
route snapshot
network interface
MTU
kernel and Scapy versions
stimulus description
control description
packet count and rate
packet-capture filenames
observed response
alternative explanations
confidence level
```

Change one independent variable at a time whenever possible.

## Known limitations

- Many tools were developed rapidly around one observed path.
- Several experiments lack packet captures from both sides of the suspected intermediary.
- Route stability is not guaranteed.
- Some scripts use fixed assumptions about hop count, target protocol, or trigger content.
- Small timing samples cannot isolate CPU load from queueing, congestion, rate limiting, or path variation.
- RDAP describes address registration, not packet-generation responsibility.
- A reset can originate from an endpoint, firewall, load balancer, hosting network, transit system, or another intermediary.
- Absence of a reset is not equivalent to successful application-layer communication.
- The tools do not yet share one normalized experiment schema.
- There is no automated replay harness against a controlled middlebox matrix.
- CI now covers the standalone artifact-integrity helper; network experiments still lack hardware-independent regression coverage.
- Historical filenames and comments can still reflect the exploratory language used during development.

## Intended use

Reverse Observer is intended for:

- private network-protocol research;
- controlled middlebox testing;
- measurement of systems owned by the researcher;
- explicitly authorized security and censorship-resilience research;
- preservation of negative results and falsified hypotheses.

It is not intended for disruption, state exhaustion of third-party infrastructure, unauthorized traffic manipulation, or claims about network operators that exceed the collected evidence.

## Development direction

Priority improvements include:

- defining one experiment-result schema;
- saving PCAPs automatically for control and stimulus runs;
- separating observations from interpretations in every script;
- recording route changes between repetitions;
- using confidence intervals rather than single RTT deltas;
- building a local test matrix with known middleboxes;
- distinguishing transport reachability from application success;
- adding endpoint-side confirmation;
- converting remaining historical claims into versioned hypotheses;
- reproducing the same experiment from multiple networks and dates;
- adding packet-construction tests and CI.

## License

See the repository license, when present, for the current terms of use.
