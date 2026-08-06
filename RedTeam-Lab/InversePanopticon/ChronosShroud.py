#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: CHRONOS SHROUD V3.0 (THE TEMPORAL BRUTE-FORCER) ---
# SYSTEM_DIRECTIVE: Find the DPI's Reassembly Timeout (T_dpi).
# TECHNIQUE: Temporal Sweep + Keep-Alive Pulsing.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class ChronosShroudV3:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.signals = []
        self.handshake_ready = threading.Event()
        self.stop_sniffer = threading.Event()
        self.keep_alive_running = False
        print(f"[+] ChronosShroud V3.0 Initialized. target: {target_host}")

    def _sniffer(self):
        def handle_pkt(pkt):
            t = time.time()
            if pkt.haslayer(IP) and pkt[IP].src == self.target_ip:
                if pkt.haslayer(TCP):
                    if pkt[TCP].flags & 0x12: # SYN-ACK
                        self.ack = pkt[TCP].seq + 1
                        self.handshake_ready.set()
                    if pkt[TCP].flags & 0x10: # ACK
                        self.signals.append(("ACK", t))
                    if pkt[TCP].flags & 0x04: # RST
                        self.signals.append(("RST", t))
        sniff(filter=f"host {self.target_ip} and tcp port {self.sport}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=150, store=0)

    def _keep_alive_pulse(self):
        """Sends empty ACKs to keep the target server's session alive during the gap."""
        while self.keep_alive_running:
            # Empty ACK resets host idle timer but provides no data for DPI reassembly
            pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack)
            send(pkt, verbose=0)
            time.sleep(5)

    def execute_session(self, gap):
        self.signals = []
        self.handshake_ready.clear()
        self.stop_sniffer.clear()
        
        t_sniff = threading.Thread(target=self._sniffer, daemon=True)
        t_sniff.start()

        # Step 1: Handshake
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        send(syn, verbose=0)
        if not self.handshake_ready.wait(timeout=5): return "Handshake Timeout"
        self.seq += 1
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)

        # Payloads
        p1 = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32)
        p2 = b"\x00\x00\x02\x13\x01\x01\x00\x00\x00\x00\x12\x00\x10\x00\x00\x0d" + self.target_host.encode()

        # Step 2: Ghost
        ghost_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq + len(p1), ack=self.ack)/p2
        send(ghost_pkt, verbose=0)

        # Step 3: Pulsed Gap
        print(f"[*] Testing Gap: {gap}s (Keep-Alive Pulse: ACTIVE)")
        self.keep_alive_running = True
        t_pulse = threading.Thread(target=self._keep_alive_pulse, daemon=True)
        t_pulse.start()
        
        t_gap_start = time.time()
        time.sleep(gap)
        self.keep_alive_running = False

        # Step 4: Anchor
        t_anchor_sent = time.time()
        anchor_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/p1
        send(anchor_pkt, verbose=0)

        # Step 5: Verdict
        time.sleep(3)
        self.stop_sniffer.set()
        
        ack_found = any(s[0] == "ACK" and s[1] > t_anchor_sent for s in self.signals)
        rst_after = [s for s in self.signals if s[0] == "RST" and s[1] > t_anchor_sent]
        
        if ack_found: return "SUCCESS"
        if rst_after: return f"DPI_PERSISTENT (RST after {rst_after[0][1] - t_anchor_sent:.3f}s)"
        return "SILENT_FAILURE"

    def run_sweep(self, start=30, end=120, step=30):
        print("\n" + "="*80)
        print("  CHRONOS SHROUD: TEMPORAL BOUNDARY SWEEP")
        print("="*80)
        print(f"{'GAP(s)':<10} {'VERDICT':<30} {'STATUS'}")
        print("-" * 80)
        
        for gap in range(start, end + 1, step):
            result = self.execute_session(gap)
            status = "[!]" if "SUCCESS" in result else "[X]"
            print(f"{gap:<10} {result:<30} {status}")
            if "SUCCESS" in result:
                print(f"\n[!] BOUNDARY FOUND: DPI flushes reassembly buffer at T < {gap}s.")
                break
            time.sleep(2) # Cooldown between tests
        print("="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--gap", type=int, default=30)
    args = parser.parse_args()
    
    engine = ChronosShroudV3(args.target)
    if args.sweep:
        engine.run_sweep()
    else:
        print(f"[*] Single Run Result: {engine.execute_session(args.gap)}")
