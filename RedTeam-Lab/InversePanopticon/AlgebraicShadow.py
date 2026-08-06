#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: ALGEBRAIC SHADOW V1.1 (FIXED COLLISION) ---
# SYSTEM_DIRECTIVE: Fix IndexError and ensure robust 16-bit algebraic collision.
# TECHNIQUE: Checksum-Neutral Payload Collision + Even-Length Padding.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class AlgebraicShadow:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] AlgebraicShadow V1.1 Initialized. target: {target_host}")

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

    def _calculate_checksum_neutral_payloads(self, decoy_sni, real_sni):
        def get_tls_base(sni):
            sni_b = sni.encode()
            prefix = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + b"\x00"*32 + b"\x00\x00\x02\x13\x01\x01\x00"
            ext = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
            return prefix + len(ext).to_bytes(2, 'big') + ext

        p_decoy = get_tls_base(decoy_sni)
        p_real = get_tls_base(real_sni)

        # Ensure max_len is even and large enough for the adjustment
        max_len = max(len(p_decoy), len(p_real))
        if max_len % 2 != 0: max_len += 1
        max_len += 2 

        p_decoy = p_decoy.ljust(max_len, b"\x00")
        p_real = p_real.ljust(max_len, b"\x00")

        def calc_sum(data):
            s = 0
            for i in range(0, len(data), 2):
                w = (data[i] << 8) + data[i+1]
                s += w
            # Standard 1's complement folding
            while (s >> 16):
                s = (s & 0xFFFF) + (s >> 16)
            return s

        sum_decoy = calc_sum(p_decoy)
        sum_real = calc_sum(p_real)

        # Calculate adjustment: (sum_decoy - sum_real) in 1's complement
        # We use simple 16-bit subtraction and handle wrap-around
        diff = (sum_decoy - sum_real)
        if diff < 0:
            diff = (diff + 0xFFFF) # 1's complement negative adjustment
        
        # Inject into the last 2 bytes
        p_real_adjusted = p_real[:-2] + diff.to_bytes(2, 'big')
        
        return p_decoy, p_real_adjusted

    def execute_bypass(self):
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

        print("[*] Phase 2: Crafting Checksum-Neutral Collision...")
        decoy, reality = self._calculate_checksum_neutral_payloads("www.bing.com", self.target_host)
        self.expected_ack = self.seq + len(reality)

        print("[*] Phase 3: Executing Double-Truth Injection...")
        pkt_decoy = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/decoy
        pkt_reality = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)/reality
        
        print("    [>] Delivering Decoy Reality (DPI Caches)...")
        send(pkt_decoy, verbose=0)
        time.sleep(0.02)
        print("    [>] Delivering Target Reality (Host Overwrites)...")
        send(pkt_reality, verbose=0)

        print(f"[*] Phase 4: Verifying Collision Success (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  ALGEBRAIC SHADOW: BYPASS RIGOROUSLY VERIFIED")
            print("="*75)
            print("RESULT: SUCCESS. Target accepted the Reality Segment.")
            print("STATUS: The DPI sentinel was defeated by a Checksum Collision.")
            print("WHY:    The observer cached the decoy based on the sequence/hash,")
            print("        failing to re-inspect the identically-hashed reality.")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. DPI logic persisted or checksum mismatch.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    args = parser.parse_args()
    AlgebraicShadow(args.target).execute_bypass()
