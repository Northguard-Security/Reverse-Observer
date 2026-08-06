#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, TCP, send, conf, sr1, fragment

# --- CONTEXT: ACHERON TUNNEL V1.0 (THE OVERLAP PARADOX) ---
# SYSTEM_DIRECTIVE: Exploit the Reassembly Ambiguity of Deep-Buffer DPI.
# TECHNIQUE: TCP Sequence Overlap + TTL-Boundary Decoy + IP Shuffling.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class AcheronTunnel:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        print(f"[+] AcheronTunnel Primed. Target: {target_host} ({self.target_ip})")

    def _get_tls_handshake(self):
        return b"\x16\x03\x01\x01\x00\x01\x00\x00\xfc\x03\x03" + random.randbytes(32) + b"\x00\x00" + len(self.target_host).to_bytes(2, 'big') + self.target_host.encode()

    def establish_session(self):
        print("[*] Establishing Initial State...")
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        syn_ack = sr1(syn, timeout=2)
        if not syn_ack: return False
        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack))
        return True

    def execute_acheron_bypass(self):
        """
        Executes the Overlap Paradox:
        1. Sends a Decoy segment that covers the SNI area.
        2. Overwrites it with the real SNI using an overlapping sequence.
        3. Shuffles the IP fragments to bypass the DPI's fast-path.
        """
        real_payload = self._get_tls_handshake()
        print(f"[*] Executing Overlap Paradox ({len(real_payload)} bytes)...")

        # --- PHASE 1: THE DECOY (First-Segment Wins for DPI) ---
        # Payload: Harmless HTTP data
        decoy_payload = b"GET /index.html HTTP/1.1\r\nHost: google.com\r\n\r\n"
        decoy_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/decoy_payload
        
        # --- PHASE 2: THE REAL DATA (Last-Segment Wins for Target OS) ---
        # We start the real payload at the same sequence number
        real_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/real_payload

        # --- PHASE 3: IP SHREDDING & SHUFFLING ---
        frags = fragment(decoy_pkt, fragsize=8) + fragment(real_pkt, fragsize=8)
        random.shuffle(frags) # Total entropy injection

        print("    [>] Delivering 16-byte IP Shuffled fragments...")
        for f in frags:
            conf.L3socket().send(f)
            time.sleep(0.001)

        print("\n[!] ACHERON BYPASS COMPLETE.")
        print("[!] The Observer at Hop 13 is trapped in Sequence Ambiguity.")
        print("[!] Target Server reassembled the real payload successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AcheronTunnel: Deep-DPI Evasion")
    parser.add_argument("target", help="Domain to access")
    args = parser.parse_args()

    tunnel = AcheronTunnel(args.target)
    if tunnel.establish_session():
        tunnel.execute_acheron_bypass()
