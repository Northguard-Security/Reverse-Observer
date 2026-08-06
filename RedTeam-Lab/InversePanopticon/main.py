#!/usr/bin/env python3
import time
import argparse
import random
import logging
import json
import urllib.request
from scapy.all import IP, TCP, ICMP, sr1, conf

# Inverse Panopticon V11
# Experimental route, RDAP-context, and differential-timing measurement tool.
# Timing classes below are descriptive buckets only; they do not identify
# hardware, vendors, DPI products, or operator intent.

conf.verb = 0
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


class TimingClass:
    HIGH_POSITIVE_DELTA = "High positive timing delta"
    MODERATE_POSITIVE_DELTA = "Moderate positive timing delta"
    NEAR_ZERO_DELTA = "Near-zero timing delta"
    UNCLASSIFIED = "Unclassified timing result"


class InversePanopticonV11:
    def __init__(self, target, max_hops=15):
        self.target = target
        self.max_hops = max_hops
        self.hops = []
        self.sport = random.randint(30000, 60000)
        self.seq = random.randint(100000, 900000)

    def _get_tls_stimulus(self):
        """Return the historical TLS-like stimulus used by this experiment."""
        payload = b"\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03" + random.randbytes(32)
        payload += b"\x20" + random.randbytes(32)
        payload += b"\x00\x20" + random.randbytes(32)
        payload += b"\x01\x00"
        extensions = b"\x00\x00\x00\x12\x00\x10\x00\x00\x0d\x74\x6f\x72\x70\x72\x6f\x6a\x65\x63\x74\x2e\x6f\x72\x67"
        extensions += b"\x00\x15" + (200).to_bytes(2, "big") + b"\x00" * 200
        payload += len(extensions).to_bytes(2, "big") + extensions
        return payload

    def get_rdap_context(self, ip):
        """Return registration context for an address via RDAP when available."""
        if ip.startswith(("192.168.", "10.", "172.16.", "127.")):
            return "Local / private address space"

        try:
            url = f"https://rdap.db.ripe.net/ip/{ip}"
            req = urllib.request.Request(url, headers={"User-Agent": "Reverse-Observer research client"})
            with urllib.request.urlopen(req, timeout=3) as response:
                data = json.loads(response.read().decode())

            name = data.get("name", "Unknown")
            country = data.get("country", "Unknown")

            if "entities" in data:
                for entity in data["entities"]:
                    if "vcardArray" not in entity:
                        continue
                    for item in entity["vcardArray"][1]:
                        if item[0] == "fn":
                            name = item[3]
                            break

            return f"{name} ({country})"
        except Exception:
            try:
                url = f"https://rdap.arin.net/registry/ip/{ip}"
                req = urllib.request.Request(url, headers={"User-Agent": "Reverse-Observer research client"})
                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode())

                name = data.get("name", "Unknown")
                if "entities" in data:
                    for entity in data["entities"]:
                        if "vcardArray" not in entity:
                            continue
                        for item in entity["vcardArray"][1]:
                            if item[0] == "fn":
                                name = item[3]
                                break
                return f"{name} (ARIN context)"
            except Exception:
                return "RDAP lookup unavailable"

    def map_route(self):
        print("[*] Mapping route topology...")
        for ttl in range(1, self.max_hops + 1):
            pkt = IP(dst=self.target, ttl=ttl) / TCP(dport=443, flags="S")
            ans = sr1(pkt, timeout=1)
            if ans and (ans.haslayer(ICMP) or ans.haslayer(TCP)):
                self.hops.append((ttl, ans.src))
                print(f"    {ttl}: {ans.src}")
                if ans.src == self.target:
                    break

    @staticmethod
    def _classify_delta(delta_ms):
        if delta_ms > 8.0:
            return TimingClass.HIGH_POSITIVE_DELTA
        if delta_ms > 1.5:
            return TimingClass.MODERATE_POSITIVE_DELTA
        if -1.5 <= delta_ms <= 1.5:
            return TimingClass.NEAR_ZERO_DELTA
        return TimingClass.UNCLASSIFIED

    def differential_timing_probe(self, hop_ip):
        """
        Compare two small ICMP RTT samples around transmission of the historical
        TLS-like stimulus.

        The resulting delta is a measurement only. Queueing, rate limiting,
        routing, scheduler noise, and many other factors can affect it.
        """
        base_rtts = []
        for _ in range(5):
            probe = IP(dst=hop_ip) / ICMP()
            t0 = time.perf_counter()
            response = sr1(probe, timeout=1)
            t1 = time.perf_counter()
            if response:
                base_rtts.append((t1 - t0) * 1000)

        if not base_rtts:
            return None, None, None

        avg_base = sum(base_rtts) / len(base_rtts)

        stimulus_rtts = []
        stimulus = (
            IP(dst=self.target)
            / TCP(sport=self.sport, dport=443, flags="PA", seq=self.seq)
            / self._get_tls_stimulus()
        )
        probe = IP(dst=hop_ip) / ICMP()

        for _ in range(5):
            conf.L3socket().send(stimulus)
            t0 = time.perf_counter()
            response = sr1(probe, timeout=1)
            t1 = time.perf_counter()
            if response:
                stimulus_rtts.append((t1 - t0) * 1000)
            time.sleep(0.1)

        if not stimulus_rtts:
            return avg_base, None, None

        avg_stimulus = sum(stimulus_rtts) / len(stimulus_rtts)
        delta = avg_stimulus - avg_base
        return avg_base, avg_stimulus, self._classify_delta(delta)

    def analyze(self):
        print("\n" + "=" * 132)
        print(
            f"{'HOP':<4} {'IP ADDRESS':<18} {'BASE':<8} {'STIM':<8} "
            f"{'DELTA':<8} {'TIMING CLASS':<34} {'RDAP CONTEXT'}"
        )
        print("=" * 132)

        for ttl, ip in self.hops:
            rdap = self.get_rdap_context(ip)

            if ip == self.target:
                print(
                    f"{ttl:<4} {ip:<18} {'-':<8} {'-':<8} {'-':<8} "
                    f"{'Target endpoint':<34} {rdap}"
                )
                continue

            base, stimulus, timing_class = self.differential_timing_probe(ip)
            if base is not None and stimulus is not None:
                delta = stimulus - base
                print(
                    f"{ttl:<4} {ip:<18} {base:<8.2f} {stimulus:<8.2f} "
                    f"{delta:<8.2f} {timing_class:<34} {rdap}"
                )
            else:
                print(
                    f"{ttl:<4} {ip:<18} {'NO RESP':<8} {'NO RESP':<8} {'-':<8} "
                    f"{'Insufficient timing data':<34} {rdap}"
                )

        print("\n[NOTE] Timing classes are descriptive. They are not hardware or vendor identification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inverse Panopticon V11: route, RDAP-context, and differential-timing experiment"
    )
    parser.add_argument("target", help="Authorized laboratory destination")
    args = parser.parse_args()

    print(f"[*] Initializing measurement against {args.target}...")
    engine = InversePanopticonV11(args.target)
    engine.map_route()
    engine.analyze()
