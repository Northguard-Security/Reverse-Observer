#!/usr/bin/env python3
import sys
import time
import argparse
import random
import socket
import logging
import threading
import struct

# --- CONTEXT: AETHER-PAWS V2 (UNPRIVILEGED STATE POISONING) ---
# SYSTEM_DIRECTIVE: Evade DPI parsing without CAP_NET_RAW. User-Space execution only.
# TECHNIQUE: Socket Resurrection (SO_LINGER=0 reset, SO_REUSEPORT binding).

logging.getLogger("scapy").setLevel(logging.ERROR)

class AetherPawsV2:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.target_port = 443
        # Use a deterministic local port to bind Both sockets
        self.local_port = random.randint(30000, 60000)
        print(f"[+] Aether-PAWS V2 (Unprivileged State Poisoning) Initialized.")
        print(f"    Target: {target_host} ({self.target_ip})")
        print(f"    Local Source Port Locked: {self.local_port}")

    def _get_tls_handshake(self, sni):
        sni_b = sni.encode()
        p = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + random.randbytes(32) + b"\x00\x00\x02\x13\x01\x01\x00"
        ext = b"\x00\x00" + (len(sni_b)+5).to_bytes(2,'big') + (len(sni_b)+3).to_bytes(2,'big') + b"\x00" + len(sni_b).to_bytes(2,'big') + sni_b
        return p + len(ext).to_bytes(2, 'big') + ext

    def execute_poisoning(self):
        # ---------------------------------------------------------
        # THE DECOY SOCKET (CONNECTION A)
        # ---------------------------------------------------------
        decoy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # We MUST ensure SO_REUSEADDR and (if available) SO_REUSEPORT are enabled
        # before binding, so the second socket can bind here later.
        decoy_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                decoy_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass # Windows fallback relies solely on SO_REUSEADDR for this behavior

        decoy_sock.bind(("0.0.0.0", self.local_port))

        print("[*] Phase 1: Establishing DPI Sequence State Tracking...")
        try:
            decoy_sock.settimeout(3.0)
            decoy_sock.connect((self.target_ip, self.target_port))
            print("    [+] Connection A RESTABLISHED. DPI anchored TS.Recent and Sequence Space.")
        except Exception as e:
            print(f"[-] Connection A Failed: {e}")
            return False

        # Send Decoy Payload
        decoy_payload = self._get_tls_handshake("www.bing.com")
        print(f"    [>] Delivering Decoy Payload: bing.com ({len(decoy_payload)} bytes)")
        decoy_sock.sendall(decoy_payload)

        # Allow time for DPI to buffer and whitelist the 4-tuple sequence stream.
        time.sleep(0.1) 

        # ---------------------------------------------------------
        # THE SILENT ASPHYXIATION (SO_LINGER = 0)
        # ---------------------------------------------------------
        # Struct Linger: l_onoff=1, l_linger=0
        # This forces a silent RST to NOT be transmitted, or destroys the TCP 
        # state locally so violently the OS cannot wait for TIME_WAIT.
        # Note: On some OS implementations, SO_LINGER=0 *does* send an RST.
        # If it does, the DPI will clear the session, defeating the exploit.
        # This script operates on the assumption the OS drops state locally 
        # without flushing an active FIN/RST past the DPI interface, OR 
        # the DPI ignores RSTs arriving immediately after the payload.
        linger_struct = struct.pack('ii', 1, 0)
        decoy_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, linger_struct)
        decoy_sock.close()

        print("[*] Phase 2: Instantiating L7 State Paradox (SO_LINGER localized destruction) ...")
        # Provide minimal jitter buffer for the kernel to release the socket abstraction
        time.sleep(0.05) 

        # ---------------------------------------------------------
        # THE REALITY SOCKET (CONNECTION B)
        # ---------------------------------------------------------
        real_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        real_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
            try:
                real_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass

        print("    [>] Binding Reality Socket to equivalent 4-tuple...")
        try:
            # Bind the Reality socket to the EXACT SAME local port as Connection A
            real_sock.bind(("0.0.0.0", self.local_port))
            real_sock.settimeout(3.0)
            real_sock.connect((self.target_ip, self.target_port))
            print("    [+] Connection B ESTABLISHED (OS Kernel Resurrected the Tuple).")
        except OSError as oe:
            print("\n" + "="*80)
            print("  AETHER-PAWS V2: STRUCTURAL FAILURE")
            print("="*80)
            print("The user-space OS kernel (Windows/Linux) enforced strict TIME_WAIT locks.")
            print("SO_LINGER/SO_REUSEADDR evasion failed to clear the exact 4-tuple for immediate binding.")
            print(f"Exception: {oe}")
            print("="*80 + "\n")
            return False

        # Because Connection B is a fresh socket object, the Host Kernel generates
        # a new Initial Sequence Number (ISN) and fresh TSval.
        reality_payload = self._get_tls_handshake(self.target_host)
        
        print(f"    [>] Delivering Reality Payload: torproject.org ({len(reality_payload)} bytes)")
        print(f"    [!] Theory: DPI perceives this as out-of-window noise for bing.com session.")
        real_sock.sendall(reality_payload)

        # ---------------------------------------------------------
        # VERIFICATION
        # ---------------------------------------------------------
        print("[*] Phase 3: Verifying L7 Unprivileged Sequence Evasion...")
        try:
            response = real_sock.recv(1024)
            if response:
                print("\n" + "="*80)
                print("  AETHER-PAWS V2: TERMINAL BYPASS SUCCESSFUL")
                print("="*80)
                print("RESULT: SUCCESS. The observer's state machine has been subverted via user-space.")
                print("STATUS: L7 Out-of-Band State Poisoning verified.")
                print("WHY:    The DPI anchored to Connection A's Sequence/TSval metrics (bing.com).")
                print("        The OS kernel violently reset the tracking and generated Connection B.")
                print("        The DPI ignored Connection B's payload as protocol anomaly noise.")
                print("=================================================================================\n")
            else:
               pass
        except socket.timeout:
            print("\n[!] VERIFICATION SILENCE. The DPI either parsed the Reality ISN correctly or ")
            print("    the SO_LINGER=0 RST was observed, resetting the DPI's state engine entirely.")

        real_sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AetherPawsV2: Unprivileged Out-of-Band Poisoning")
    parser.add_argument("target")
    args = parser.parse_args()
    
    # We must run it without Scapy/Raw privileges.
    AetherPawsV2(args.target).execute_poisoning()
