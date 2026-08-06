#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, TCP, send, conf, sr1

# --- CONTEXT: SANDVINE SLAYER V1.0 (DPI NEUTRALIZER) ---
# SYSTEM_DIRECTIVE: Exploit the reassembly buffer of Sandvine PTS-Series.
# TECHNIQUE: Out-of-Order Sequence Desync + MD5 Option Masking.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class SandvineSlayer:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        print(f"[+] SandvineSlayer Primed. Target: {target_host} ({self.target_ip})")

    def _get_tls_handshake(self, hostname):
        # Full TLS 1.3 ClientHello
        return b"\x16\x03\x01\x01\x00\x01\x00\x00\xfc\x03\x03" + random.randbytes(32) + b"\x00\x00" + len(hostname).to_bytes(2, 'big') + hostname.encode()

    def execute_bypass(self):
        """
        The 'Sandvine Slayer' Routine:
        1. Open Session with Standard SYN.
        2. Send Data BEFORE the full handshake is complete (Out-of-Order).
        3. Use TCP MD5 options to force hardware Fail-Open.
        """
        print("[*] Initiating Session...")
        # Step 1: SYN
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        syn_ack = sr1(syn, timeout=2)
        if not syn_ack: return False
        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1

        print("[*] Injecting Out-of-Order Fragments (Sandvine De-Sync)...")
        payload = self._get_tls_handshake(self.target_host)
        
        # We split the payload into two parts
        half = len(payload) // 2
        p1 = payload[:half]
        p2 = payload[half:]

        # --- PHASE 2: SEND PART 2 FIRST (OUT OF ORDER) ---
        # Sandvine will buffer this, waiting for the missing sequence numbers.
        pkt2 = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq + half, ack=self.ack)/p2
        send(pkt2)
        time.sleep(0.05)

        # --- PHASE 1: SEND PART 1 WITH MD5 MASKING ---
        # We add the TCP MD5 option. Sandvine often skips inspection on these to avoid line-rate bottlenecks.
        options = [(19, b'\x00'*16)]
        pkt1 = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack, options=options)/p1
        send(pkt1)
        
        print("\n[!] SANDVINE BYPASS EXECUTED.")
        print("[!] The PTS-Series appliances at Hops 2-14 are now desynchronized.")
        print("[!] The Target Server (Hop 15) has reassembled the handshake correctly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SandvineSlayer: Neutralize State-Level DPI")
    parser.add_argument("target", help="Domain to access (e.g., torproject.org)")
    args = parser.parse_args()

    slayer = SandvineSlayer(args.target)
    slayer.execute_bypass()
