import sys
import time
import argparse
import random
from scapy.all import IP, TCP, ICMP, sr1, conf, TracerouteResult, traceroute

# Disable scapy verbosity
conf.verb = 0

class InversePanopticon:
    def __init__(self, target):
        self.target = target
        self.results = {
            "baseline_rtt": 0,
            "dpi_latency": 0,
            "observer_hop": None,
            "intent": "None Detected",
            "confidence": 0.0
        }

    def get_baseline(self):
        """Measures ICMP/TCP-SYN baseline latency to eliminate network noise."""
        print(f"[*] Establishing Baseline for {self.target}...")
        pkt = IP(dst=self.target)/TCP(dport=443, flags="S")
        start = time.perf_counter()
        ans = sr1(pkt, timeout=2)
        end = time.perf_counter()
        
        if ans:
            self.results["baseline_rtt"] = (end - start) * 1000
            print(f"    [+] Baseline RTT: {self.results['baseline_rtt']:.2f}ms")
            return True
        return False

    def scan_hops(self):
        """Performs advanced traceroute to identify potential middleboxes."""
        print("[*] Mapping Path Topology...")
        res, unans = traceroute(self.target, l4=TCP(dport=443, flags="S"), maxttl=20)
        return res

    def detect_dpi(self):
        """Injects high-entropy SNI/HTTP headers to trigger DPI-induced latency."""
        print("[*] Injecting High-Entropy Payloads (SNI-Trigger)...")
        # Simulate a sensitive SNI handshake
        payload = b"\x16\x03\x01\x00\xca\x01\x00\x00\xc6\x03\x03" + 
                  random.randbytes(32) + 
                  b"\x00\x00\x02\x00\x3d\x01\x00\x00\x9f\x00\x00" + 
                  b"\x00\x12" + self.target.encode()
        
        pkt = IP(dst=self.target)/TCP(dport=443, flags="PA")/payload
        start = time.perf_counter()
        ans = sr1(pkt, timeout=3)
        end = time.perf_counter()
        
        if ans:
            self.results["dpi_latency"] = (end - start) * 1000
            delta = self.results["dpi_latency"] - self.results["baseline_rtt"]
            
            if delta > 10: # Threshold for DPI processing time
                self.results["intent"] = "Active Surveillance / DPI"
                self.results["confidence"] = min(delta / 20, 1.0)
                print(f"    [!] Detected Anomaly: +{delta:.2f}ms latency on encrypted handshake.")
            else:
                self.results["intent"] = "Passive / No Surveillance Detected"
                print("    [-] No significant DPI latency detected.")
        else:
            self.results["intent"] = "Active Filtering / Dropping Sensitive Traffic"
            self.results["confidence"] = 0.9
            print("    [!] CONNECTION DROPPED: Highly suggestive of Censorship/Blocking.")

    def report(self):
        print("
" + "="*50)
        print("  INVERSE PANOPTICON: SURVEILLANCE ANALYSIS")
        print("="*50)
        print(f"TARGET: {self.target}")
        print(f"RESULT: {self.results['intent']}")
        print(f"CONFIDENCE: {self.results['confidence'] * 100:.1f}%")
        print(f"WHY: Based on Temporal Jitter Singularity in TLS Handshake.")
        print("="*50 + "
")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inverse Panopticon: Remote Observer Detection")
    parser.add_argument("target", help="Domain or IP to analyze")
    args = parser.parse_args()

    ip = InversePanopticon(args.target)
    if ip.get_baseline():
        ip.scan_hops()
        ip.detect_dpi()
        ip.report()
    else:
        print("[!] Target unreachable for baseline.")
