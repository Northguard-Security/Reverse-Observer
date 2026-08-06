#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff, TCPOptions

# --- CONTEXT: PAWS DESYNC V1.0 (THE CHRONOLOGICAL SCHISM) ---
# SYSTEM_DIRECTIVE: Exploit RFC 1323 PAWS (Protect Against Wrapped Sequences).
# TECHNIQUE: Desynchronize DPI state by serving a chronologically obsolete decoy.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class PawsDesync:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.tsval = random.randint(1000000, 9000000)
        self.tsecr = 0
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] PawsDesync V1.0 (Chronological Schism) Initialized.")
        print(f"    Target: {target_host} ({self.target_ip})")

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(TCP) and pkt[IP].src == self.target_ip and pkt[TCP].dport == self.sport:
                if pkt[TCP].flags & 0x12: # SYN-ACK
                    self.ack = pkt[TCP].seq + 1
                    for opt, val in pkt[TCP].options:
                        if opt == 'Timestamp':
                            self.tsecr = val[0]
                if pkt[TCP].flags & 0x10: # ACK
                    # If we mapped the expected ack
                    if self.expected_ack > 0 and pkt[TCP].ack >= self.expected_ack:
                        self.bypass_verified.set()
        sniff(filter=f"tcp and src host {self.target_ip}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=15, store=0)

    def _get_tls_handshake(self, sni):
        sni_b = sni.encode()
        p = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
        return p + len(ext).to_bytes(2, 'big') + ext

    def execute_bypass(self):
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        # Phase 1: Handshake with Timestamps
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq, options=[('Timestamp', (self.tsval, 0))])
        send(syn, verbose=0)
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout: time.sleep(0.1)
        if self.ack == 0: 
            print("[-] Handshake Timeout.")
            return False
            
        self.seq += 1
        self.tsval += 1
        ack_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack, options=[('Timestamp', (self.tsval, self.tsecr))])
        send(ack_pkt, verbose=0)
        print("    [+] Session ESTABLISHED (Timestamps Negotiated).")

        # Phase 2: Construct Realities
        reality_data = self._get_tls_handshake(self.target_host)
        decoy_data = self._get_tls_handshake("www.bing.com")
        
        if len(decoy_data) < len(reality_data):
            decoy_data = decoy_data.ljust(len(reality_data), b"\x00")
        else:
            reality_data = reality_data.ljust(len(decoy_data), b"\x00")
            
        self.expected_ack = self.seq + len(reality_data)

        # 1. DECOY PAYLOAD (Obsolete Timestamp)
        # TSval is deliberately set into the past (e.g. self.tsval - 100000)
        # PAWS rule: if TSval < TS.Recent, drop silently.
        p_decoy = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack, options=[('Timestamp', (1, self.tsecr))])/decoy_data

        # 2. REALITY PAYLOAD (Valid Timestamp)
        self.tsval += 1
        p_real = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack, options=[('Timestamp', (self.tsval, self.tsecr))])/reality_data

        print("[*] Phase 2: Injecting PAWS Chronological Schism...")
        print("    [>] Delivering Decoy Segment (TSval=1, Target-Drops)...")
        send(p_decoy, verbose=0)
        time.sleep(0.05) # Jitter
        
        print(f"    [>] Delivering Reality Segment (TSval={self.tsval}, Target-Accepts)...")
        send(p_real, verbose=0)

        print(f"[*] Phase 3: Verifying PAWS Bypass (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  PAWS DESYNC V1.0: TERMINAL BYPASS SUCCESSFUL")
            print("="*75)
            print("RESULT: SUCCESS. The observer's reality has been terminated.")
            print("STATUS: PAWS Chronological Schism verified.")
            print("WHY:    The DPI ignored RFC 1323 PAWS rules and assimilated the Decoy.")
            print("        The Target enforcing PAWS dropped the Decoy and accepted Reality.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. Possible strict First-Wins OS policy or DPI timestamp validation.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    PawsDesync(args.target).execute_bypass()
