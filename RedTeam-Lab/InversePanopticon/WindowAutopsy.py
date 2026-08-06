#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sniff, sr1

# --- CONTEXT: WINDOW AUTOPSY V1.0 (EMPIRICAL RIGOR) ---
# SYSTEM_DIRECTIVE: Systematically identify the DPI inspection depth.
# TECHNIQUE: Incremental Bit-Shift Offset Probing.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class WindowAutopsy:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.results = {} # Offset -> Boolean (RST Triggered)
        self.stop_sniffer = threading.Event()
        self.rst_detected = threading.Event()

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(IP) and pkt[IP].src == self.target_ip:
                if pkt.haslayer(TCP) and pkt[TCP].flags & 0x04:
                    self.rst_detected.set()
        sniff(filter=f"tcp and src host {self.target_ip} and dst port {self.sport}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), store=0)

    def probe_offset(self, offset):
        """Sends the target string at a specific byte offset."""
        self.rst_detected.clear()
        # Payload: Padded with nulls to push the 'trigger' further into the packet
        padding = b"\x00" * offset
        trigger = self.target_host.encode()
        payload = padding + trigger
        
        # We use PA flags to simulate data injection
        pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=0)/payload
        send(pkt, verbose=0)
        
        # Wait for the RST
        triggered = self.rst_detected.wait(timeout=1.5)
        return triggered

    def run_audit(self):
        print(f"[*] Starting Rigorous Inspection Window Audit for {self.target_host}...")
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        # Step-wise increments to find the boundary
        offsets = [0, 8, 16, 24, 32, 40, 48, 56, 64, 128, 256]
        
        print(f"{'OFFSET(bytes)':<15} {'STATUS':<15} {'VERDICT'}")
        print("-" * 45)
        
        boundary_found = False
        for off in offsets:
            triggered = self.probe_offset(off)
            status = "TRIGGERED" if triggered else "CLEAN"
            verdict = "Visible" if triggered else "Invisible (BYPASS)"
            
            self.results[off] = triggered
            print(f"{off:<15} {status:<15} {verdict}")
            
            if not triggered and any(self.results.values()) and not boundary_found:
                print(f"    [!] DISCOVERY: Inspection boundary identified at byte {off}.")
                boundary_found = True
            
            time.sleep(0.5) # Prevent rate-limiting

        self.stop_sniffer.set()
        
        print("-" * 45)
        if not any(self.results.values()):
            print("[!] Result: No active RST-censorship detected on this path.")
        else:
            max_visible = max([k for k, v in self.results.items() if v])
            print(f"[+] RIGOROUS VERDICT: The observer's depth limit is {max_visible} bytes.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WindowAutopsy: Find the exact DPI depth.")
    parser.add_argument("target", help="Target domain (e.g., torproject.org)")
    args = parser.parse_args()

    autopsy = WindowAutopsy(args.target)
    autopsy.run_audit()
