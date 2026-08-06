#!/usr/bin/env python3
import time
import argparse
import random
import socket
import logging
import threading
import json
from pathlib import Path
from scapy.all import IP, TCP, ICMP, send, conf, sniff, sr1

# --- CONTEXT: ENTROPY MASK V11 (ANALYTIC LEDGER) ---
# PURPOSE: Persist route and trigger-response observations without treating
#          route position, source address, TTL, or timing as proof of a
#          particular middlebox implementation or operator policy.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

LEDGER_PATH = Path(__file__).resolve().parent / "IntelligenceLedger.jsonl"


class EntropyMaskV11:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.hops_map = {}
        self.detected_rsts = []
        self.stop_sniffer = threading.Event()
        print("[+] EntropyMask V11 (Analytic Ledger) initialized.")

    def _get_dynamic_tls_bait(self):
        """Build the historical TLS-like stimulus used by this experiment."""
        sni = self.target_host.encode()
        header = b"\x16\x03\x01"
        ch_body = (
            b"\x03\x03"
            + random.randbytes(32)
            + b"\x00"
            + b"\x00\x02\x13\x01\x01\x00"
        )
        ext_sni = (
            b"\x00\x00"
            + (len(sni) + 5).to_bytes(2, "big")
            + (len(sni) + 3).to_bytes(2, "big")
            + b"\x00"
            + len(sni).to_bytes(2, "big")
            + sni
        )
        ch_body += len(ext_sni).to_bytes(2, "big") + ext_sni
        handshake = b"\x01\x00" + len(ch_body).to_bytes(3, "big") + ch_body
        return header + len(handshake).to_bytes(2, "big") + handshake

    def _rst_sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(IP) and pkt[IP].src == self.target_ip:
                if pkt.haslayer(TCP) and pkt[TCP].flags & 0x04:
                    self.detected_rsts.append(
                        {
                            "received_ttl": int(pkt[IP].ttl),
                            "timestamp": time.time(),
                        }
                    )

        sniff(
            filter=f"tcp and src host {self.target_ip} and dst port {self.sport}",
            prn=handle_pkt,
            stop_filter=lambda _: self.stop_sniffer.is_set(),
            store=0,
        )

    def map_route(self):
        print("[*] Mapping path with TCP probes...")
        for ttl in range(1, 25):
            pkt = IP(dst=self.target_ip, ttl=ttl) / TCP(
                sport=self.sport,
                dport=443,
                flags="S",
                seq=self.seq,
            )
            ans = sr1(pkt, timeout=1, verbose=0)
            if ans:
                self.hops_map[ttl] = ans.src
                if not ans.haslayer(ICMP):
                    break

    def log_result(self, record):
        """Append one observation record to the repository-local ledger."""
        with LEDGER_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        print(f"[*] Observation persisted to {LEDGER_PATH.name}")

    def analyze(self):
        self.map_route()
        if not self.hops_map:
            print("[!] No route observations collected.")
            return

        t = threading.Thread(target=self._rst_sniffer, daemon=True)
        t.start()

        print("[*] Sweeping TTL horizon...")
        first_trigger_ttl = None
        first_rst = None
        bait_payload = self._get_dynamic_tls_bait()

        for ttl in range(1, len(self.hops_map) + 1):
            pre_count = len(self.detected_rsts)
            bait = IP(dst=self.target_ip, ttl=ttl) / TCP(
                sport=self.sport,
                dport=443,
                flags="PA",
                seq=self.seq + 1,
                ack=0,
            ) / bait_payload
            send(bait, verbose=0)
            time.sleep(0.8)

            if len(self.detected_rsts) > pre_count:
                first_trigger_ttl = ttl
                first_rst = self.detected_rsts[-1]
                break

        self.stop_sniffer.set()

        if first_trigger_ttl is None:
            record = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "target": self.target_host,
                "target_ip": self.target_ip,
                "route_length_observed": max(self.hops_map),
                "first_trigger_ttl": None,
                "observation": "no matching TCP reset observed during this sweep",
            }
            self.log_result(record)
            print("[i] No matching TCP reset observed during the tested sweep.")
            return

        hop_ip = self.hops_map.get(first_trigger_ttl)
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "target": self.target_host,
            "target_ip": self.target_ip,
            "route_length_observed": max(self.hops_map),
            "first_trigger_ttl": first_trigger_ttl,
            "hop_address_at_same_ttl": hop_ip,
            "received_rst_ttl": first_rst["received_ttl"] if first_rst else None,
            "observation": "matching TCP reset observed after the selected stimulus",
            "interpretation": (
                "The TTL sweep constrains where the response became observable in this "
                "measurement. It does not uniquely identify the packet generator, hardware "
                "class, vendor, network operator policy, or a censorship device."
            ),
        }
        self.log_result(record)

        print("\n" + "=" * 78)
        print("  ENTROPY MASK: MEASUREMENT RESULT")
        print("=" * 78)
        print(f"TARGET:                 {self.target_host} ({self.target_ip})")
        print(f"FIRST TRIGGER TTL:      {first_trigger_ttl}")
        print(f"HOP AT SAME TTL:        {hop_ip or 'Unknown'}")
        print(f"RECEIVED RST TTL:       {record['received_rst_ttl']}")
        print("INTERPRETATION:         Trigger-associated response observed.")
        print("                        Generator/vendor/hardware not established.")
        print("=" * 78 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EntropyMask V11: persist bounded route/response observations"
    )
    parser.add_argument("target", help="Authorized laboratory destination")
    args = parser.parse_args()
    EntropyMaskV11(args.target).analyze()
