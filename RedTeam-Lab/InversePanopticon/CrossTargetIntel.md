# Inverse Panopticon: Cross-Target Comparison Notes

**Date:** March 1, 2026

This file preserves an early comparison between measurements involving multiple destinations. Later experiments invalidated part of the original interpretation, so the conclusions are narrowed here.

## 1. Recorded comparison

The original notes compared response behavior observed while probing destinations including `torproject.org` and `wikileaks.org`.

Different response patterns were observed across those runs.

That difference can be useful, but it does not uniquely establish a target-specific enforcement policy. Different destinations can also produce different results because of:

- destination-side firewall or application behavior;
- route changes;
- different hosting and transit networks;
- load balancing;
- address-family differences;
- temporary network conditions;
- probe construction and TCP-state differences.

## 2. Superseded shallow-window hypothesis

The original report described the `torproject.org` path as using a shallow 32-byte inspection window and suggested that a valid TLS 1.3 structure escaped that window.

Later `TriggerValidator` and offset experiments **falsified that explanation under the tested conditions**: the selected trigger was still associated with reset behavior when moved well beyond the first 32 bytes, including the larger tested offsets.

Therefore the shallow-window conclusion should not be used as a current project finding.

## 3. UDP/TCP difference

The experiments also observed different response behavior for selected TCP/443 and UDP/443 probes.

This is a protocol-dependent observation, not proof that all carrier-level controls were bypassed. A complete comparison requires successful end-to-end application validation, not merely the absence of a TCP-style reset signal.

## 4. Current value of this file

The cross-target work demonstrates why controls are necessary. A response that appears destination-specific can only be interpreted after controlling for route, endpoint, protocol, timing, and probe state.

This document is retained as a record of an early hypothesis and its later correction.
