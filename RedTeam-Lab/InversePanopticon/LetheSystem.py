#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: LETHE SYSTEM V1.0 (SYMMETRIC GHOSTING) ---
# SYSTEM_DIRECTIVE: Force state-eviction via spoofed server-side termination.
# TECHNIQUE: Symmetric State Ambiguity + Inverted TTL-limited FIN.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class LetheSystem:
    def __init__(self, target_host, censor_hop=13):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.local_ip = [l for l in ([ip for j in socket.gethostbyname_ex(socket.gethostname())[2] if not j.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
        self.censor_hop = censor_hop
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.target_seq = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] LetheSystem Initialized. Target: {target_host} ({self.target_ip})")
        print(f"[+] Target Observer: Hop {censor_hop} (Symmetric State-Table)")

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(TCP) and pkt[IP].src == self.target_ip and pkt[TCP].dport == self.sport:
                if pkt[TCP].flags & 0x12: # SYN-ACK
                    self.target_seq = pkt[TCP].seq
                    self.ack = self.target_seq + 1
                if pkt[TCP].flags & 0x10: # ACK
                    # Success if target ACKs the data sent AFTER the server-ghosting
                    if hasattr(self, 'expected_ack') and pkt[TCP].ack >= self.expected_ack:
                        self.bypass_verified.set()
        sniff(filter=f"tcp and src host {self.target_ip}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=15, store=0)

    def execute_lethe(self):
        # Start Sniffer
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        print("[*] Phase 1: Establishing Legitimate 3-Way Handshake...")
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        send(syn, verbose=0)
        
        # Wait for sniffer to catch SYN-ACK and set self.ack
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout:
            time.sleep(0.1)
        
        if self.ack == 0:
            print("[!] Handshake Failed.")
            return False

        self.seq += 1
        # Send 3rd ACK
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)
        print(f"    [+] Session ESTABLISHED. LocalSeq: {self.seq}, RemoteSeq: {self.ack}")

        print(f"[*] Phase 2: Injecting Symmetric Ghost-FIN (Spoofed Server -> Client)...")
        # --- THE CORE EXPLOIT ---
        # We spoof a packet FROM the server TO us.
        # We calculate the TTL so it reaches the DPI (Hop 13) but dies before reaching us (or is ignored).
        # Received_TTL from V10 was 51. Forward distance 13.
        # We send with TTL=3 to hit the DPI from the 'Server Side' perspective (simulated).
        # Actually, we must send it from OUR interface with a TTL that reaches the DPI.
        # To the DPI, a packet with src=Target_IP and flags=FIN means the server is closing.
        server_ghost = IP(src=self.target_ip, dst=self.local_ip, ttl=self.censor_hop)/TCP(sport=443, dport=self.sport, flags="FA", seq=self.ack, ack=self.seq)
        send(server_ghost, verbose=0)
        
        print("    [>] DPI state-table eviction signal delivered.")
        time.sleep(0.2)

        print("[*] Phase 3: Delivering Sensitive Reality (SNI: torproject.org)...")
        payload = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00\x00\x00\x00\x12\x00\x10\x00\x00\x0d" + self.target_host.encode()
        self.expected_ack = self.seq + len(payload)
        
        data_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/payload
        send(data_pkt, verbose=0)

        print(f"[*] Phase 4: Verifying Symmetric Bypass (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*70)
            print("  LETHE SYSTEM: BYPASS SUCCESSFUL")
            print("="*70)
            print("STATUS: The DPI reassembler has been 'Symmetrically Ghosted'.")
            print("WHY:    The observer accepted the spoofed server-termination,")
            print("        leaving the end-to-end reality un-inspected.")
            print("="*70 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. Observer logic persists.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--hop", type=int, default=13)
    args = parser.parse_args()
    
    LetheSystem(args.target, censor_hop=args.hop).execute_lethe()
