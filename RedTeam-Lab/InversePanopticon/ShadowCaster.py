#!/usr/bin/env python3
import argparse
import random
import logging
from scapy.all import IP, TCP, ICMP, sr1, conf

# ShadowCaster
# Experimental ICMP quotation-comparison tool.
# The script records structural differences in returned quotations. Those
# differences are not sufficient to identify a vendor, product, or agency.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


class QuotationObservation:
    HEADER_DIFF = "Quoted IP header differs from transmitted header"
    TTL_DIFF = "Quoted header includes a TTL difference"
    SHORT_QUOTE = "Short ICMP quotation observed"
    TCP_OPTION_DIFF = "Quoted TCP options differ"
    NO_SPECIAL_PATTERN = "No selected quotation pattern observed"
    NO_RESPONSE = "No qualifying ICMP Time Exceeded response"


class ShadowCaster:
    def __init__(self, target, max_hops=15):
        self.target = target
        self.max_hops = max_hops
        self.hops = []
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)

    def _get_probe_packet(self, ttl):
        """Create a packet with a unique payload for quotation comparison."""
        payload = b"INV_PANOPTICON_" + random.randbytes(16)
        return IP(dst=self.target, ttl=ttl) / TCP(
            sport=self.sport,
            dport=443,
            flags="PA",
            seq=self.seq,
        ) / payload

    def map_route(self):
        print("[*] Mapping route for quotation measurements...")
        for ttl in range(1, self.max_hops + 1):
            pkt = IP(dst=self.target, ttl=ttl) / TCP(dport=443, flags="S")
            ans = sr1(pkt, timeout=1)
            if ans and (ans.haslayer(ICMP) or ans.haslayer(TCP)):
                self.hops.append((ttl, ans.src))
                print(f"    {ttl}: {ans.src}")
                if ans.src == self.target:
                    break

    def inspect_quotation(self, ttl):
        """Compare an ICMP Time Exceeded quotation with the transmitted packet."""
        original = self._get_probe_packet(ttl)
        ans = sr1(original, timeout=1.5)

        if not (ans and ans.haslayer(ICMP) and ans.getlayer(ICMP).type == 11):
            return [QuotationObservation.NO_RESPONSE]

        quoted = ans.getlayer(ICMP).payload
        observations = []

        try:
            if bytes(original[IP])[:20] != bytes(quoted)[:20]:
                observations.append(QuotationObservation.HEADER_DIFF)
        except Exception:
            pass

        try:
            if quoted.haslayer(IP) and quoted[IP].ttl != original[IP].ttl:
                observations.append(QuotationObservation.TTL_DIFF)
        except Exception:
            pass

        try:
            if len(bytes(quoted)) < 28:
                observations.append(QuotationObservation.SHORT_QUOTE)
        except Exception:
            pass

        try:
            if original.haslayer(TCP) and quoted.haslayer(TCP):
                if original[TCP].options != quoted[TCP].options:
                    observations.append(QuotationObservation.TCP_OPTION_DIFF)
        except Exception:
            pass

        if not observations:
            observations.append(QuotationObservation.NO_SPECIAL_PATTERN)

        return observations

    def analyze(self):
        print("\n" + "=" * 110)
        print(f"{'HOP':<4} {'IP ADDRESS':<20} {'QUOTATION OBSERVATION'}")
        print("=" * 110)

        for ttl, ip in self.hops:
            if ip == self.target:
                continue

            observations = self.inspect_quotation(ttl)
            print(f"{ttl:<4} {ip:<20} {'; '.join(observations)}")

        print(
            "\n[NOTE] Quotation differences are descriptive observations only; "
            "they do not identify a DPI vendor or hardware platform."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ShadowCaster: ICMP quotation comparison experiment"
    )
    parser.add_argument("target", help="Authorized laboratory destination")
    args = parser.parse_args()

    caster = ShadowCaster(args.target)
    caster.map_route()
    caster.analyze()
