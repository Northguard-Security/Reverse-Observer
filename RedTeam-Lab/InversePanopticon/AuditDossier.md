# Inverse Panopticon: Path Measurement Snapshot

**Target used in the original experiment:** `torproject.org`  
**Date:** March 1, 2026

This document records an early route/timing snapshot. It should not be interpreted as proof of a surveillance architecture, a specific DPI product, or the intent of any network operator.

## 1. Observed route context

The experiment recorded responsive hops associated through RDAP or local addressing with several networks along the measured path.

| Layer in original notes | Example hop | Network context | What was actually observed |
| :--- | :--- | :--- | :--- |
| Access | 2 | Local / ISP-side address space | A responsive hop on the measured route |
| Transit | 8 | Twelve99 / Arelion-associated address | A measurable RTT difference during the stimulus run |
| Destination-side | 15 | Hetzner-associated address | A responsive hop near the destination path |

RDAP ownership and route position do not identify which system generated a later TCP reset, nor do they establish a device type or policy intent.

## 2. Timing observation

The original run recorded an approximately **+10.08 ms** difference at one transit hop between two small timing samples.

The early report labeled this as evidence of a software-defined DPI bottleneck. That conclusion was too strong.

A timing delta of this size can also arise from:

- ordinary queueing;
- ICMP rate limiting;
- scheduler variation;
- ECMP or route changes;
- transient congestion;
- control-plane processing;
- unrelated host or network load.

The defensible result is therefore:

> A positive timing delta was observed in that run; its cause was not uniquely identified.

## 3. Follow-up value

The useful next experiment is not to infer hardware from RTT, but to reproduce the same control/stimulus comparison across:

- many repetitions;
- stable route snapshots;
- multiple source networks;
- controlled middleboxes with known implementations;
- packet capture on both sides of the test device.

This file is preserved as part of the chronological research record. Later conclusions supersede the stronger terminology used in the original version.
