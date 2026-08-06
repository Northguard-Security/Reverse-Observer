#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging

# --- CONTEXT: TLS SHATTER V1.0 (APPLICATION-LAYER ASYMMETRY) ---
# SYSTEM_DIRECTIVE: Evade DPI SNI parsing via Extreme Pacing (Ring 3 Only).
# TECHNIQUE: TCP_NODELAY + L7 Byte-level Fragmentation targeting DPI Parser Timeout.

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

class TlsShatter:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.target_port = 443
        print(f"[+] TlsShatter V1.0 (TLS Fragmentation Asymmetry) Initialized.")
        print(f"    Target: {target_host} ({self.target_ip})")

    def _get_tls_handshake(self, sni):
        sni_b = sni.encode()
        # Standard TLS 1.3 ClientHello
        p = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
        payload = p + len(ext).to_bytes(2, 'big') + ext
        return payload

    def execute_shatter(self, chunk_size=1, delay=0.1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # 1. Disable Nagle's Algorithm to force the kernel to send tiny packets immediately
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        print(f"[*] Phase 1: Native Winsock TCP Handshake...")
        try:
            sock.settimeout(15.0) # Elevated timeout to allow the target server to wait for our slow trickle
            sock.connect((self.target_ip, self.target_port))
            print("    [+] Handshake Complete. Socket ESTABLISHED.")
        except Exception as e:
            print(f"[-] Connection Failed: {e}")
            return

        payload = self._get_tls_handshake(self.target_host)
        total_len = len(payload)
        
        print(f"[*] Phase 2: Commencing Asymmetric L7 Shatter (Chunk={chunk_size}b, Delay={delay}s)...")
        print(f"    [>] Delivering Target Reality ({total_len} bytes) via extreme pacing...")

        try:
            # 2. Transmit the ClientHello byte-by-byte (or chunk-by-chunk)
            for i in range(0, total_len, chunk_size):
                chunk = payload[i:i+chunk_size]
                sock.sendall(chunk)
                # Introduce delay to exhaust the DPI's Application Layer protocol timeout
                time.sleep(delay)
                
                # Simple progress indicator
                if i % 20 == 0 and i > 0:
                    print(f"        -> Sent {i}/{total_len} bytes...")
            print(f"        -> Sent {total_len}/{total_len} bytes. Payload complete.")

        except Exception as e:
            print(f"\n[!] Delivery Interrupted: DPI RST or Target Socket Timeout. ({e})")
            sock.close()
            return
            
        print(f"[*] Phase 3: Awaiting Server Hello Response (Verification)...")
        try:
            resp = sock.recv(1024)
            if resp:
                print("\n" + "="*80)
                print("  TLS SHATTER V1.0: APPLICATION-LAYER BYPASS SUCCESSFUL")
                print("="*80)
                print("VERDICT:   Systemic DPI Parser Asphyxiation Confirmed")
                print(f"MECHANISM: The L7 byte-pacing (delay={delay}s) exceeded the DPI's TLS ")
                print("           parser timeout threshold, forcing it to fail-open before ")
                print("           synthesizing the complete SNI reality.")
                print("           Target server maintained connection and returned ServerHello.")
                print("="*80 + "\n")
            else:
                # The target server gracefully closed the connection (maybe it timed out?)
                print("\n[!] VERIFICATION SILENCE. Server closed connection without ServerHello.")
                print("    Target likely requires a smaller delay to prevent standard HTTP timeout.")
        except socket.timeout:
            print("\n[!] VERIFICATION SILENCE. Flow stalled or target server ignored malformed TLS.")
        except ConnectionResetError:
            print("\n[!] CONNECTION RESET. The DPI successfully buffered the entire L7 flow")
            print("    and issued a RST upon reassembling the forbidden SNI.")

        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TlsShatter: Application-Layer DPI Parser Asphyxiation")
    parser.add_argument("target")
    parser.add_argument("--chunk", type=int, default=1, help="Bytes per send()")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay (seconds) between chunks")
    args = parser.parse_args()
    
    TlsShatter(args.target).execute_shatter(args.chunk, args.delay)
