#!/usr/bin/env python3
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, sr1, conf, send

# GhostDeceptor V1.0
# Historical TCP sequence-overlap and zero-window experiment.
# The script transmits the selected construction but does not contain an
# end-to-end oracle capable of proving what an intermediary reassembled.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


class GhostDeceptor:
    def __init__(self, target_host, target_port=443):
        self.target_host = target_host
        self.target_port = target_port
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.target_ip = socket.gethostbyname(target_host)
        print(f"[+] GhostDeceptor initialized. Destination: {target_host} ({self.target_ip})")

    def _get_control_sni(self):
        """Historical control TLS-like payload containing google.com."""
        return (
            b"\x16\x03\x01\x01\x00\x01\x00\x00\xfc\x03\x03"
            + random.randbytes(32)
            + b"\x00\x00\x00\x0c\x67\x6f\x6f\x67\x6c\x65\x2e\x63\x6f\x6d"
        )

    def _get_target_sni(self, hostname):
        """Historical target TLS-like payload."""
        return (
            b"\x16\x03\x01\x01\x00\x01\x00\x00\xfc\x03\x03"
            + random.randbytes(32)
            + b"\x00\x00"
            + len(hostname).to_bytes(2, "big")
            + hostname.encode()
        )

    def handshake(self):
        """Establish the TCP state used by the experiment."""
        print("[*] Establishing TCP handshake...")
        options = [("MSS", 1460), ("NOP", None), ("WScale", 7)]
        syn = IP(dst=self.target_ip) / TCP(
            sport=self.sport,
            dport=self.target_port,
            flags="S",
            seq=self.seq,
            options=options,
        )
        syn_ack = sr1(syn, timeout=2)

        if not syn_ack:
            print("[!] No SYN/ACK observed.")
            return False

        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1

        ack_pkt = IP(dst=self.target_ip) / TCP(
            sport=self.sport,
            dport=self.target_port,
            flags="A",
            seq=self.seq,
            ack=self.ack,
        )
        send(ack_pkt)
        print("    [+] TCP handshake completed.")
        return True

    def inject_overlap_experiment(self):
        """
        Transmit the historical two-packet sequence-overlap construction.

        Transmission success only means the local sender emitted the packets.
        This function does not verify which representation, if any, an
        intermediary or the destination accepted.
        """
        print(f"[*] Sending overlap experiment for {self.target_host}...")

        control_data = self._get_control_sni()
        target_data = self._get_target_sni(self.target_host)

        ttl_limited = IP(dst=self.target_ip, ttl=10) / TCP(
            sport=self.sport,
            dport=self.target_port,
            flags="PA",
            seq=self.seq,
            ack=self.ack,
        ) / control_data

        normal_ttl = IP(dst=self.target_ip, ttl=64) / TCP(
            sport=self.sport,
            dport=self.target_port,
            flags="PA",
            seq=self.seq,
            ack=self.ack,
        ) / target_data

        print("    [>] Sending TTL-limited control segment...")
        send(ttl_limited)
        time.sleep(0.01)
        print("    [>] Sending overlapping normal-TTL segment...")
        send(normal_ttl)

        self.seq += len(target_data)
        print(f"    [+] Experiment packets transmitted. Current sequence: {self.seq}")

    def maintain_zero_window_experiment(self):
        """Transmit periodic zero-window ACKs used by the historical experiment."""

        def worker():
            while True:
                pkt = IP(dst=self.target_ip) / TCP(
                    sport=self.sport,
                    dport=self.target_port,
                    flags="A",
                    seq=self.seq,
                    ack=self.ack,
                    window=0,
                )
                send(pkt, verbose=0)
                time.sleep(10)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        print("    [+] Periodic zero-window experiment started.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GhostDeceptor: historical TCP overlap measurement experiment"
    )
    parser.add_argument("target", help="Authorized laboratory destination")
    args = parser.parse_args()

    experiment = GhostDeceptor(args.target)
    if experiment.handshake():
        experiment.maintain_zero_window_experiment()
        experiment.inject_overlap_experiment()
        print("\n[RESULT] The packet construction was transmitted.")
        print("[BOUNDARY] No verified intermediary desynchronization is established by this script.")
        print("[BOUNDARY] Endpoint and middlebox reassembly require independent observation to compare.")
