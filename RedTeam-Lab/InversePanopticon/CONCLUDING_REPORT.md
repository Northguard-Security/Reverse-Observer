# Inverse Panopticon: Concluding Measurement Report

**Measurement window:** March 1–2, 2026  
**Revision:** 4  
**Status:** empirical observations with bounded interpretation

---

## 1. Path context

The experiments measured selected routes toward `torproject.org` and recorded response behavior associated with hops whose address space was registered through RDAP to networks including Twelve99/Arelion and Hetzner.

RDAP and route position provide **network context**, not proof of responsibility for a particular reset, filtering policy, appliance, or implementation.

The current interpretation deliberately separates:

- the network that an IP address is registered to;
- the hop at which a response became observable;
- the system that actually generated the response;
- the policy or implementation that caused it.

Those are not automatically the same thing.

---

## 2. Measurement methodology

The investigation used several small tools to vary protocol properties and observe the resulting network responses.

- **InversePanopticon V11** — route probing, RDAP context, and differential timing experiments.
- **EntropyMask V11** — TTL sweeps and transport-dependent response comparison.
- **ShadowCaster** — ICMP quotation comparison.
- **TriggerValidator** — comparison of selected raw and structured TLS stimuli.
- **ChronosShroud V3** — delayed delivery tests for out-of-order TCP state behavior.
- Additional scripts explored checksums, fragmentation, sequence overlap, TCP options, and related edge cases.

The suite was developed iteratively around one observed environment. It is not a standardized censorship-measurement platform and does not provide a direct middlebox state oracle.

---

## 3. Trigger-related observations

### 3.1 Offset and TLS tests

The following responses were recorded during the tested session:

| Test | Observation |
| :--- | :--- |
| Raw `torproject.org` near offset 0 | TCP reset behavior observed |
| Raw `torproject.org` near offset 256 | TCP reset behavior observed |
| Structured TLS-like ClientHello containing the selected SNI | TCP reset behavior observed |

These observations are sufficient to reject the early **“32-byte-only shallow inspection window”** explanation under the tested conditions.

They do **not**, by themselves, uniquely prove a complete TLS parser. A response could still be produced by several forms of stateful or content-aware inspection.

The defensible result is:

> The selected trigger remained observable beyond the first few dozen bytes and inside the structured TLS-like stimulus used by the experiment.

### 3.2 Delayed state experiment

`ChronosShroud V3` recorded trigger-associated behavior after delayed delivery of out-of-order TCP material through the tested range:

| Gap (s) | Recorded reset delay after anchor |
| :--- | :--- |
| 10 | 213 ms |
| 30 | 51 ms |
| 60 | 46 ms |
| 90 | 56 ms |
| 120 | 48 ms |

This is consistent with some state being retained through the tested delays.

It does not prove the exact internal buffer structure, timeout implementation, or location of that state.

---

## 4. TCP state and reassembly experiments

The following table summarizes whether the tested construction changed the observed trigger behavior.

| Tool | Experimental variable | Result under tested conditions | Evidence level |
| :--- | :--- | :--- | :--- |
| ChronosShroud | temporal gap | trigger behavior persisted | observed |
| PhlegethonSink | TTL-limited FIN | no verified middlebox-state eviction | observed endpoint behavior; intermediary state unobserved |
| LetheSystem | reverse-direction FIN hypothesis | no verified state change | observed |
| ReassemblyScythe | 128-segment pressure case | no fail-open behavior observed | observed for tested intensity |
| OmniDesync | ACK/window manipulation | no verified state change | observed |
| ChecksumShadow | invalid-checksum decoy | expected trigger was not produced by invalid decoy | observed |
| StyxTunnel | IP-fragment overlap case | selected trigger remained observable | observed |
| AlgebraicShadow | sequence overlap case | selected trigger remained observable | observed |
| AlgebraicStyx | fragment constructions | no verified evasion | observed / partially incomplete |
| SingularPoint | sequence wrap and TCP options | selected trigger remained observable | observed |
| HyperionFlux | TLS extension overlap case | selected trigger remained observable | observed |
| NeuralFlux | overlap hypothesis | no rigorous result | unverified |
| ProtocolOblivion | cross-protocol reconstruction idea | endpoint construction invalid | structurally invalid |

These results are best read as **behavioral constraints on the tested hypotheses**, not as proof of a particular product's complete capabilities.

---

## 5. TCP versus UDP observation

One recurring result was a difference between selected TCP/443 and UDP/443 probes:

- TCP experiments produced the reset behavior being measured;
- UDP/443 probes did not produce an equivalent TCP-style reset signal.

The original notes called this a confirmed QUIC/UDP bypass. That wording is withdrawn.

The experiment did not establish a complete application-layer QUIC session as the success condition, so the stronger claim is not supported.

The current conclusion is:

> The measured path showed transport-dependent response behavior during the March 2026 observation window.

That difference may reflect policy, implementation, endpoint behavior, or another network condition and should be re-measured rather than treated as permanent.

---

## 6. Open diagnostic questions

The following questions remain unresolved:

1. **Upper bound of retained state** — testing stopped at 120 seconds.
2. **Response origin** — route and TTL evidence do not uniquely identify the component that generated each reset.
3. **Cross-path reproducibility** — different source routes produced different observations.
4. **Transport semantics** — UDP reachability needs application-level confirmation rather than inference from missing TCP signals.
5. **Reassembly semantics** — several constructions need validation in a controlled middlebox where both ingress and egress can be captured.
6. **Encrypted Client Hello** — where deployed, ECH changes the visibility of SNI-related metadata and should be treated as a separate modern measurement case.

---

## 7. Behavioral profile derived from the experiments

The strongest defensible statements from the recorded tests are:

| Observation | Supporting experiment |
| :--- | :--- |
| selected content remained associated with reset behavior beyond a very shallow byte window | TriggerValidator / offset tests |
| delayed out-of-order TCP material still contributed to the later trigger through the tested delay range | ChronosShroud |
| invalid-checksum traffic behaved differently from the valid comparison | ChecksumShadow |
| tested fragment and sequence-overlap constructions did not remove the selected trigger | StyxTunnel / AlgebraicShadow / AlgebraicStyx |
| selected wrap-around and option combinations did not suppress the observed response | SingularPoint |
| the tested TLS-overlap construction did not suppress the observed response | HyperionFlux |
| a TTL-limited FIN did not provide verified evidence of intermediary state eviction | PhlegethonSink |
| UDP/443 and TCP/443 produced different observable responses in the tested session | EntropyMask / related probes |

None of these observations identifies a commercial vendor or hardware class on its own.

---

## 8. Falsified or unsupported hypotheses

| Hypothesis | Current status |
| :--- | :--- |
| “The inspection window is limited to the first ~32 bytes” | **falsified under tested conditions** |
| “A simple raw-string-only explanation is sufficient” | **not supported as a complete explanation** |
| “The tested temporal gaps flush the relevant state” | **falsified through 120 s test range** |
| “TTL-limited Ghost-FIN proves middlebox state eviction” | **falsified as a verified claim** |
| “An invalid-checksum decoy suppresses the later trigger” | **falsified under tested conditions** |
| “The tested IP-fragment overlap produces a verified reassembly asymmetry” | **not observed** |
| “The tested 32-bit wrap case breaks the observed state handling” | **not observed** |
| “NeuralFlux bypass was verified” | **unverified** |
| “ProtocolOblivion reconstructs across protocol boundaries” | **structurally invalid** |
| “UDP/443 without a TCP-style reset proves a QUIC bypass” | **unsupported by the success condition used** |

---

## 9. Research conclusion

The most useful result of the project is not a bypass claim. It is the progressive elimination of explanations that did not survive measurement.

The March 2026 work supports a narrower conclusion:

> A selected path exhibited repeatable, stateful, content-sensitive, and transport-dependent response behavior under a set of raw-packet experiments. Several initially attractive explanations were falsified, while the exact implementation and response origin remained underdetermined.

Future work should prioritize controlled middleboxes, packet capture on both sides, repeated baselines, endpoint confirmation, and statistical treatment of timing data.

---

*This report summarizes historical measurements and the current interpretation of those measurements.*  
*Raw tool output and `IntelligenceLedger.jsonl`, where present, should take precedence over narrative wording.*
