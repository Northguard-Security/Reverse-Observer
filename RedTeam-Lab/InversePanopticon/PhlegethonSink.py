#!/usr/bin/env python3
import time
import argparse
import random
import socket
import logging
import threading
from scapy.all import IP, TCP, send, conf, sr1, sniff

# PhlegethonSink V2.0
# Experimental TTL-limited FIN / post-FIN endpoint-response measurement.
# A qualifying ACK from the endpoint confirms endpoint behavior only. It does
# not reveal whether an unseen intermediary retained, changed, or discarded
# its internal flow state.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


class PhlegethonSinkV2:
    def __init__(self, target_host, censor_hop=13):
        self.target_host = target_host
        self.target_ip = socket.gethostbyname(target_host)
        self.censor_hop = censor_hop
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)
        self.ack = 0
        self.target_responded = threading.Event()
        self.stop_sniffer = threading.Event()
        self.expected_ack = 0
        print(f"[+] PhlegethonSink V2.0 initialized for {target_host}")

    def _sniffer(self):
        """Monitor for an endpoint ACK covering the post-FIN payload."""

        def handle_pkt(pkt):
            if not (pkt.haslayer(IP) and pkt.haslayer(TCP)):
                return
            if pkt[IP].src != self.target_ip or pkt[TCP].dport != self.sport:
                return

            if pkt[TCP].flags & 0x10:
                if self.expected_ack > 0 and pkt[TCP].ack >= self.expected_ack:
                    self.target_responded.set()

        sniff(
            filter=f"tcp and src host {self.target_ip}",
            prn=handle_pkt,
            stop_filter=lambda _: self.stop_sniffer.is_set(),
            timeout=15,
            store=0,
        )

    def execute_sink(self):
        listener = threading.Thread(target=self._sniffer, daemon=True)
        listener.start()

        print("[*] Phase 1: establishing TCP session...")
        syn = IP(dst=self.target_ip) / TCP(
            sport=self.sport,
            dport=443,
            flags="S",
            seq=self.seq,
        )
        syn_ack = sr1(syn, timeout=2, verbose=0)
        if not syn_ack:
            print("[!] No SYN/ACK observed; experiment stopped.")
            self.stop_sniffer.set()
            return False

        self.ack = syn_ack[TCP].seq + 1
        self.seq += 1
        send(
            IP(dst=self.target_ip)
            / TCP(sport=self.sport, dport=443, flags="A", seq=self.seq, ack=self.ack),
            verbose=0,
        )
        print(f"    [+] TCP session established. Initial sequence: {self.seq}")

        print(f"[*] Phase 2: sending TTL-limited FIN (TTL={self.censor_hop})...")
        fin_pkt = IP(dst=self.target_ip, ttl=self.censor_hop) / TCP(
            sport=self.sport,
            dport=443,
            flags="FA",
            seq=self.seq,
            ack=self.ack,
        )
        send(fin_pkt, verbose=0)
        time.sleep(0.1)

        print("[*] Phase 3: sending post-FIN TLS-like stimulus...")
        payload = (
            b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03"
            + random.randbytes(32)
            + b"\x00\x00\x02\x13\x01\x01\x00\x00\x00\x00\x12\x00\x10\x00\x00\x0d"
            + self.target_host.encode()
        )
        self.expected_ack = self.seq + len(payload)

        data_pkt = IP(dst=self.target_ip) / TCP(
            sport=self.sport,
            dport=443,
            flags="PA",
            seq=self.seq,
            ack=self.ack,
        ) / payload
        send(data_pkt, verbose=0)

        print(f"[*] Phase 4: waiting for endpoint ACK >= {self.expected_ack}...")
        if self.target_responded.wait(timeout=5):
            print("\n" + "=" * 74)
            print("PHLEGETHON SINK: ENDPOINT ACK OBSERVED")
            print("=" * 74)
            print("OBSERVED: The destination acknowledged data sent after the TTL-limited FIN.")
            print("BOUNDARY: This does not prove that any intermediary evicted flow state.")
            print("NEEDED:   A direct middlebox-state oracle or controlled ingress/egress capture")
            print("          is required for that stronger conclusion.")
            print("=" * 74 + "\n")
            result = True
        else:
            print("\n[!] No qualifying endpoint ACK observed within the measurement window.")
            result = False

        self.stop_sniffer.set()
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PhlegethonSink: TTL-limited FIN endpoint-response experiment"
    )
    parser.add_argument("target", help="Authorized laboratory destination")
    parser.add_argument("--hop", type=int, default=13, help="TTL used for the FIN probe")
    args = parser.parse_args()

    PhlegethonSinkV2(args.target, censor_hop=args.hop).execute_sink()
