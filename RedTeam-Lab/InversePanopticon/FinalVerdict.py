#!/usr/bin/env python3
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, ICMP, send, conf, sniff, sr1

# FinalVerdict.py
# Historical offset-response experiment retained for reproducibility.
# The tool records whether a TCP RST is observed after selected stimuli. It does
# not identify a censor, determine an inspection-window size, or infer hardware.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


class FinalVerdict:
    def __init__(self, target_host):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.hops = {}
        self.rst_captured = []
        self.stop_sniffer = threading.Event()

    def _sniffer(self):
        def handle_pkt(pkt):
            if pkt.haslayer(IP) and pkt[IP].src == self.target_ip:
                if pkt.haslayer(TCP) and pkt[TCP].flags & 0x04:
                    self.rst_captured.append(pkt[IP].ttl)

        sniff(
            filter=f"tcp and src host {self.target_ip} and dst port {self.sport}",
            prn=handle_pkt,
            stop_filter=lambda _: self.stop_sniffer.is_set(),
            store=0,
        )

    def map_path(self):
        print(f"[*] Mapping measured path to {self.target_ip}...")
        for ttl in range(1, 25):
            pkt = IP(dst=self.target_ip, ttl=ttl) / TCP(
                sport=self.sport,
                dport=443,
                flags="S",
                seq=self.seq,
            )
            ans = sr1(pkt, timeout=1, verbose=0)
            if ans:
                self.hops[ttl] = ans.src
                if not ans.haslayer(ICMP):
                    break

        if not self.hops:
            return None
        return max(self.hops.keys())

    def first_rst_offset(self, max_dist):
        """
        Return the first tested offset for which this run observed a matching RST.

        The historical implementation intentionally stops at the first matching
        offset, so this result cannot be interpreted as the size or boundary of
        an inspection window.
        """
        print("[*] Running selected offset-response probes...")
        listener = threading.Thread(target=self._sniffer, daemon=True)
        listener.start()

        offsets = [0, 16, 32, 64, 128, 256]
        first_offset = None
        observed_ttl = None

        for offset in offsets:
            self.rst_captured = []
            payload = b"\x00" * offset + b"torproject.org"
            pkt = IP(dst=self.target_ip, ttl=max_dist) / TCP(
                sport=self.sport,
                dport=443,
                flags="PA",
                seq=self.seq + 1,
                ack=0,
            ) / payload
            send(pkt, verbose=0)
            time.sleep(1)

            if self.rst_captured:
                first_offset = offset
                observed_ttl = self.rst_captured[0]
                print(
                    f"    [OBSERVED] Matching RST after tested offset {offset} "
                    f"(received TTL {observed_ttl})"
                )
                break

        self.stop_sniffer.set()
        return first_offset, observed_ttl

    def run(self):
        print(f"[+] Offset-response experiment initialized for {self.target_host}")
        max_dist = self.map_path()

        if max_dist is None:
            print("[!] No responsive path hops were recorded; experiment stopped.")
            return

        offset, rst_ttl = self.first_rst_offset(max_dist)

        print("\n" + "=" * 80)
        print("OFFSET-RESPONSE MEASUREMENT")
        print("=" * 80)
        print(f"TARGET: {self.target_host} ({self.target_ip})")

        if offset is not None:
            print(f"FIRST TESTED OFFSET WITH MATCHING RST: {offset} bytes")
            print(f"RECEIVED RST TTL: {rst_ttl}")
            print("INTERPRETATION: A reset followed this tested stimulus in this run.")
            print("BOUNDARY: The experiment stops at the first match, so it does not")
            print("          determine an inspection-window boundary or response origin.")
        else:
            print("OBSERVATION: No matching RST was recorded for the tested offsets.")
            print("BOUNDARY: This does not prove that the path is transparent or unfiltered.")

        print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Historical TCP offset-response measurement experiment"
    )
    parser.add_argument("target", help="Authorized laboratory destination")
    args = parser.parse_args()
    FinalVerdict(args.target).run()
