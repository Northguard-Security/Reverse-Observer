#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, TCP, send, conf, sr1

# --- CONTEXT: TRIGGER VALIDATOR V2.0 (THE TRUTH SEEKER) ---
# SYSTEM_DIRECTIVE: Determine if the censor is Protocol-Aware or a Dumb-Regex.
# TECHNIQUE: Structured vs Malformed Comparative Probing.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class TriggerValidator:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)

    def _send_bait(self, name, payload):
        print(f"[*] Testing {name}...")
        # We use PA flags to simulate data in a perceived session
        pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=0)/payload
        ans = sr1(pkt, timeout=2, verbose=0)
        if ans and ans.haslayer(TCP) and ans[TCP].flags & 0x04:
            print(f"    [!] {name}: TRIGGERED RST (Censor Active)")
            return True
        print(f"    [-] {name}: NO RESPONSE (Censor Silent)")
        return False

    def run(self):
        # 1. MALFORMED (SNI at Offset 0)
        malformed_payload = b"\x16\x03\x01\x00\xc6\x01\x00\x00\xc2\x03\x03" + self.target_host.encode()
        
        # 2. STRUCTURED (Valid TLS 1.3, SNI at Offset ~60)
        sni = self.target_host.encode()
        structured_payload = b"\x16\x03\x01\x00\x40\x01\x00\x00\x3c\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        structured_payload += b"\x00\x00" + (len(sni)+5).to_bytes(2,'big') + (len(sni)+3).to_bytes(2,'big') + b"\x00" + len(sni).to_bytes(2,'big') + sni

        print(f"[*] Trigger Validation against {self.target_ip}...")
        res_malformed = self._send_bait("MALFORMED_OFFSET_0", malformed_payload)
        time.sleep(1)
        res_structured = self._send_bait("STRUCTURED_TLS_1.3", structured_payload)

        print("\n" + "="*70)
        print("  TRIGGER VALIDATION: THE FINAL VERDICT")
        print("="*70)
        if res_malformed and not res_structured:
            print("VERDICT: Censor is a DUMB REGEX (Offset-Sensitive).")
            print("STRATEGY: Bypass is achieved by standard RFC-compliance.")
        elif res_malformed and res_structured:
            print("VERDICT: Censor is an ADVANCED DPI (Protocol-Aware).")
            print("STRATEGY: Bypass requires Protocol Shifting (UDP/QUIC) or Desync.")
        elif not res_malformed and not res_structured:
            print("VERDICT: No active censorship detected on this path.")
        print("="*70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    TriggerValidator(args.target).run()
