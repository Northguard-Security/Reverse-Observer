# Inverse Panopticon: Route and Protocol Observation

**Target used in the original experiment:** `torproject.org`  
**Date:** March 1, 2026

This document preserves an intermediate measurement snapshot. The original version presented several inferences as definitive attribution; those claims are narrowed here to what the experiment actually observed.

## 1. Route context

A TCP-based TTL sweep associated one responsive hop near the destination path with address space registered to **Hetzner Online GmbH (AS24940)**.

That establishes route and registration context only.

It does **not** prove that:

- this hop generated every observed reset;
- Hetzner intentionally applied the observed policy;
- a particular appliance or software stack was responsible;
- the response originated physically at the router represented by that hop.

## 2. Protocol-dependent observation

The original run recorded different behavior between selected TCP/443 and UDP/443 probes.

| Probe class | Recorded observation |
| :--- | :--- |
| TCP/443 stimulus | TCP reset behavior was observed in the tested path/session |
| UDP/443 probe | No equivalent TCP-style reset signal was observed |

The earlier report labeled the UDP result as a successful bypass. That is too strong.

Absence of a TCP reset on UDP does not prove:

- successful QUIC negotiation;
- application-layer reachability;
- absence of filtering;
- a permanent policy difference;
- a general method for avoiding inspection.

The correct conclusion is simply that the **observable response differed by transport in that measurement window**.

## 3. Follow-up

A stronger protocol comparison would verify end-to-end application behavior and collect packet captures at both endpoints, ideally against a controlled test service.

No deployment or tunneling recommendation is made from this snapshot.
