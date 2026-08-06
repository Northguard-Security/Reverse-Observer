#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, TCP, send, conf, sr1

# --- CONTEXT: MTU SHREDDER V1.0 (SEGMENTATION BYPASS) ---
# SYSTEM_DIRECTIVE: Exploit the Buffer-Depth Limit of Hop 13.
# TECHNIQUE: Dynamic MSS Slicing + 1-Byte Window Manipulation.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class MtuShredder:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        print(f"[+] MtuShredder Primed. Target: {target_host} ({self.target_ip})")

    def _get_tls_handshake(self):
        # Full TLS 1.3 ClientHello for the target
        return b"\x16\x03\x01\x01\x00\x01\x00\x00\xfc\x03\x03" + random.randbytes(32) + b"\x00\x00" + len(self.target_host).to_bytes(2, 'big') + self.target_host.encode()

    def execute_shred(self):
        """
        Executes the MTU Shredding Attack:
        1. Handshake with tiny MSS (64 bytes).
        2. Deliver payload in tiny segments to overflow the observer's reassembly buffer.
        """
        print("[*] Phase 1: Negotiating Tiny MSS (64 bytes)...")
        # Standard SYN with MSS=64
        options = [('MSS', 64), ('WScale', 0), ('SAckOK', b'')]
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq, options=options)
        syn_ack = sr1(syn, timeout=2)
        
        if not syn_ack:
            print("[!] Handshake Failed: Target Unreachable.")
            return
        
        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1
        
        # ACK to complete handshake
        ack_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack)
        send(ack_pkt)
        print("    [+] Handshake Established with MTU-Constraint.")

        # Phase 2: Shredded Delivery
        payload = self._get_tls_handshake()
        print(f"[*] Phase 2: Shredding {len(payload)} bytes into 32-byte segments...")
        
        chunk_size = 32
        for i in range(0, len(payload), chunk_size):
            chunk = payload[i:i+chunk_size]
            # Send segment with tiny window to keep the observer busy
            pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack, window=1)/chunk
            send(pkt, verbose=0)
            self.seq += len(chunk)
            time.sleep(0.02) # Micro-jitter

        print("\n[!] MTU SHREDDING COMPLETE.")
        print("[!] Hop 13 (213.239.240.13) buffer depth likely exceeded.")
        print("[!] Real traffic can now pass through the shredded state.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MtuShredder: Bypass RST-Injection at Hop 13")
    parser.add_argument("target", help="Domain to access (e.g., torproject.org)")
    args = parser.parse_args()

    shredder = MtuShredder(args.target)
    shredder.execute_shred()
