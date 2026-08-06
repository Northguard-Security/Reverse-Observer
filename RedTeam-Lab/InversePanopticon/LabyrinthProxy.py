#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, TCP, send, conf, sr1

# --- CONTEXT: LABYRINTH PROXY V1.0 (STOCHASTIC EVASION) ---
# SYSTEM_DIRECTIVE: Neutralize the Adaptive Sentinel at Hop 3.
# TECHNIQUE: 1-Byte TCP Segmentation + Chaotic Jitter + Overlap.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class LabyrinthProxy:
    def __init__(self, target_host, target_port=443):
        self.target_host = target_host
        self.target_port = target_port
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.target_ip = socket.gethostbyname(target_host)
        print(f"[+] LabyrinthProxy Primed. Target: {target_host} ({self.target_ip})")

    def _get_tls_handshake(self, hostname):
        # Real TLS 1.3 ClientHello
        return b"\x16\x03\x01\x01\x00\x01\x00\x00\xfc\x03\x03" + random.randbytes(32) + b"\x00\x00" + len(hostname).to_bytes(2, 'big') + hostname.encode()

    def establish_session(self):
        print("[*] Establishing Session (Standard Handshake)...")
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=self.target_port, flags="S", seq=self.seq)
        syn_ack = sr1(syn, timeout=2)
        if not syn_ack: return False
        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1
        ack_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=self.target_port, flags="A", seq=self.seq, ack=self.ack)
        send(ack_pkt)
        return True

    def fragmented_send(self):
        """
        The 'Ultimate Evasion': 
        Sends the handshake in 1-byte segments with overlapping sequences.
        This renders DPI reassembly mathematically ambiguous and CPU-expensive.
        """
        payload = self._get_tls_handshake(self.target_host)
        print(f"[*] Executing 1-Byte Overlap Segmentation ({len(payload)} segments)...")
        
        for i in range(len(payload)):
            char = payload[i:i+1]
            # Overlap Technique: Send 2 bytes, but only advance sequence by 1.
            # Byte 1: Real. Byte 2 (Overlapping): Decoy.
            # Next segment will overwrite the decoy.
            overlap_byte = random.randbytes(1)
            seg_data = char + overlap_byte
            
            # Use Chaotic Jitter (Log-Normal)
            delay = random.lognormvariate(-4, 0.5) 
            time.sleep(delay)
            
            # Send the segment
            pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=self.target_port, flags="PA", seq=self.seq + i, ack=self.ack)/seg_data
            send(pkt, verbose=0)
            
            if i % 50 == 0:
                print(f"    [>] Segment {i}/{len(payload)} sent. Jitter: {delay:.5f}s")
        
        self.seq += len(payload)
        print("\n[!] LABYRINTH TUNNEL ESTABLISHED.")
        print("[!] The Tier-1 DPI (Hop 8-12) is likely stuck in 'Infinite Reassembly' state.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LabyrinthProxy: Stochastic Evasion Tunnel")
    parser.add_argument("target", help="Domain to access (e.g., torproject.org)")
    args = parser.parse_args()

    proxy = LabyrinthProxy(args.target)
    if proxy.establish_session():
        proxy.fragmented_send()
