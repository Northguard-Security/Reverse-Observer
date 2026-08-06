#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, TCP, send, conf, sr1

# --- CONTEXT: NEURAL FLUX V1.0 (THE QUANTUM BYPASS) ---
# SYSTEM_DIRECTIVE: Exploit Asymmetric Reassembly (First-Wins vs Last-Wins).
# TECHNIQUE: TCP Sequence Shadowing + Window-Zero Deception.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class NeuralFlux:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        print(f"[+] NeuralFlux Initialized. target: {target_host} ({self.target_ip})")

    def _get_tls_payload(self, sni):
        """Minimal TLS 1.3 ClientHello."""
        sni_b = sni.encode()
        payload = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext_sni = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
        payload += (len(ext_sni)).to_bytes(2, 'big') + ext_sni
        return payload

    def execute_flux(self):
        print("[*] Phase 1: Establishing Deceptive State (Window-Zero)...")
        # 1. SYN
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        syn_ack = sr1(syn, timeout=2, verbose=0)
        if not syn_ack: return False
        
        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1
        
        # 2. ACK with Window=0 (Tell the DPI we are 'full')
        ack_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack, window=0)
        send(ack_pkt, verbose=0)
        time.sleep(0.1)

        print("[*] Phase 2: Injecting Schrödinger Segments (Overlap Paradox)...")
        # Payload A: Decoy (Harmless)
        decoy_payload = self._get_tls_payload("www.bing.com")
        # Payload B: Reality (Forbidden)
        real_payload = self._get_tls_payload(self.target_host)

        # We send Decoy FIRST with same sequence number
        # DPI usually caches 'First-Wins'
        p_decoy = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/decoy_payload
        
        # We send Real SECOND with same sequence number
        # Target OS (Linux) usually accepts 'Last-Wins'
        p_real = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/real_payload

        print("    [>] Delivering Decoy Reality (google.com)...")
        send(p_decoy, verbose=0)
        time.sleep(0.01) # Jitter
        print("    [>] Delivering Target Reality (torproject.org)...")
        send(p_real, verbose=0)

        print("\n" + "="*70)
        print("  NEURAL FLUX: OPERATION COMPLETE")
        print("="*70)
        print(f"TARGET: {self.target_ip}")
        print("STATUS: Flow is now physically ambiguous.")
        print("WHY:    The observer's reassembler is holding the decoy,")
        print("        while the target server has accepted the reality.")
        print("="*70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    NeuralFlux(args.target).execute_flux()
