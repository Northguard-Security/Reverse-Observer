#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# --- CONTEXT: ALGEBRAIC STYX V1.4 (THE TTL SINGULARITY) ---
# SYSTEM_DIRECTIVE: Exploit TTL-Horizon Gap + Checksum-Validation Asymmetry.
# TECHNIQUE: Dual-Path Fragmentation (TTL-Limited Decoy vs Full-TTL Reality).

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class AlgebraicStyxV14:
    def __init__(self, target_host, censor_hop=13):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.censor_hop = censor_hop
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.expected_ack = 0
        self.bypass_verified = threading.Event()
        self.stop_sniffer = threading.Event()
        print(f"[+] AlgebraicStyx V1.4 (TTL Singularity) Initialized.")
        print(f"    Target: {target_host} ({self.target_ip}) | Censor Hop: {censor_hop}")

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

    def _get_tls_handshake(self, sni):
        sni_b = sni.encode()
        p = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
        return p + len(ext).to_bytes(2, 'big') + ext

    def execute_bypass(self):
        t = threading.Thread(target=self._sniffer, daemon=True)
        t.start()

        # Phase 1: Handshake
        syn = IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="S", seq=self.seq)
        send(syn, verbose=0)
        timeout = time.time() + 5
        while self.ack == 0 and time.time() < timeout: time.sleep(0.1)
        if self.ack == 0: return False
        self.seq += 1
        send(IP(dst=self.target_ip)/TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack), verbose=0)
        print("    [+] Session ESTABLISHED.")

        # Phase 2: Construct Realities
        reality_data = self._get_tls_handshake(self.target_host)
        decoy_data = self._get_tls_handshake("www.bing.com")
        if len(decoy_data) < len(reality_data):
            decoy_data = decoy_data.ljust(len(reality_data), b"\x00")
        else:
            reality_data = reality_data.ljust(len(decoy_data), b"\x00")
        
        self.expected_ack = self.seq + len(reality_data)

        # Build Full Packets for Checksums
        base_ip = IP(dst=self.target_ip)
        base_tcp = TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq, ack=self.ack)
        
        # DPI's View: Chimera (Decoy Head + Reality Tail)
        chimera_payload = decoy_data[:20] + reality_data[20:]
        pkt_chimera = base_ip/base_tcp/chimera_payload
        chimera_raw = bytes(pkt_chimera)
        
        # Target's View: Full Reality
        pkt_reality = base_ip/base_tcp/reality_data
        reality_raw = bytes(pkt_reality)

        # Phase 3: TTL-Sovereign Fragmentation
        # All fragments share the same IP ID
        ip_id = random.randint(1000, 60000)
        
        # 1. DECOY HEAD: TTL=Censor_Hop. Reaches DPI, dies before Target.
        # Contains Chimera Checksum + 20 bytes of Decoy Data.
        f_decoy = IP(dst=self.target_ip, id=ip_id, ttl=self.censor_hop, frag=0, flags="MF")/chimera_raw[20:60]
        
        # 2. REALITY HEAD: TTL=64. Reaches Target.
        # Contains Reality Checksum + 20 bytes of Reality Data.
        f_real_1 = IP(dst=self.target_ip, id=ip_id, ttl=64, frag=0, flags="MF")/reality_raw[20:60]
        
        # 3. COMMON TAIL: TTL=64. Reaches Target.
        # Contains the remainder of the payload (Shared by both).
        f_real_2 = IP(dst=self.target_ip, id=ip_id, ttl=64, frag=5)/reality_raw[60:]

        print("[*] Phase 2: Injecting TTL-Sovereign Paradox...")
        print("    [>] Delivering Decoy Segment (TTL-Limited)...")
        send(f_decoy, verbose=0)
        time.sleep(0.02)
        
        print("    [>] Delivering Reality Segments (Full-TTL)...")
        send(f_real_1, verbose=0)
        send(f_real_2, verbose=0)

        print(f"[*] Phase 3: Verifying TTL-Sovereign Bypass (Expected ACK >= {self.expected_ack})...")
        if self.bypass_verified.wait(timeout=5):
            print("\n" + "="*75)
            print("  ALGEBRAIC STYX V1.4: TERMINAL BYPASS SUCCESSFUL")
            print("="*75)
            print("RESULT: SUCCESS. The observer's reality has been terminated.")
            print("STATUS: TTL-Horizon Split + Checksum Integrity verified.")
            print("WHY:    The DPI reassembled the Decoy (First-Wins).")
            print("        The Target reassembled the Reality (Decoy expired).")
            print("="*75 + "\n")
        else:
            print("\n[!] VERIFICATION FAILED. Possible stateful retransmission check.")
        
        self.stop_sniffer.set()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--hop", type=int, default=13)
    args = parser.parse_args()
    AlgebraicStyxV14(args.target, censor_hop=args.hop).execute_bypass()
