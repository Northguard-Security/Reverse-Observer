# Inverse Panopticon: Session Comparison Notes

**Target used in the original experiment:** `torproject.org`  
**Date:** March 1, 2026 — Session 2

This file compares observations from two measurement sessions. It does not establish that a network operator changed policy or that a particular DPI device became active between runs.

## 1. Timing difference at an early hop

The second session recorded a larger latency delta at Hop 3 (`10.66.231.253`) than the first session, including a value of approximately **+17.81 ms** in the original notes.

The earlier interpretation described this as a software-defined DPI becoming behaviorally active. The measurement itself does not support that level of attribution.

Possible explanations include:

- queueing and local load;
- route or ECMP differences;
- ICMP/control-plane rate limiting;
- scheduler variance;
- transient congestion;
- different processing paths inside the provider network;
- a stateful inspection component.

The last possibility remains a hypothesis rather than a unique conclusion.

## 2. Transit and destination-side observations

Several Twelve99- and Hetzner-associated hops responded differently across probes and sessions. Timeouts or delayed responses were originally labeled as “shunning” and assigned hardware classes.

Those labels are withdrawn.

A router that does not answer a probe may simply rate-limit, deprioritize, filter, or omit that control-plane response while continuing to forward data normally.

## 3. Current interpretation

The two sessions demonstrate that **single-run timing fingerprints are unstable**.

They do not, by themselves, demonstrate:

- adaptive censorship;
- a behaviorally triggered inspection mode;
- ASIC versus software implementation;
- deliberate evasion countermeasures.

The useful result is methodological: route, timing, and response behavior must be repeated and statistically characterized before architectural claims are made.
