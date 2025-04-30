import os
import signal
import subprocess
import argparse
import time
from subprocess import Popen
from typing import List, TextIO

def run_smcrouted(log_file: str) -> Popen[bytes]:
    f: TextIO = open(log_file, "w")
    return subprocess.Popen(
        ["sudo", "smcrouted", "-n", "-l", "debug"
    ], stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, preexec_fn=os.setsid)

def run_tcpdump_igmp(interface: str, out_file: str) -> Popen[bytes]:
    f: TextIO = open(out_file, "w")
    return subprocess.Popen([
        "sudo", "tcpdump", "-i", interface, "-l", "-vvv", "igmp"
    ], stdout=f, stderr=subprocess.STDOUT, preexec_fn=os.setsid)

def run_tcpdump_udp(interface: str, mcast_ip: str, mcast_port: str, out_file: str) -> Popen[bytes]:
    return subprocess.Popen([
        "sudo", "tcpdump", "-i", interface, "-n", "-s", "0",
        "udp", "and", "dst", "host", mcast_ip, "and", "dst", "port", mcast_port,
        "-w", out_file
    ], preexec_fn=os.setsid)

def run_tsp(ip: str, log_file: str, mcast_ip: str, mcast_port: str) -> Popen[bytes]:
    f: TextIO = open(log_file, "w")
    return subprocess.Popen([
        "tsp", "-v", "-I", "ip", mcast_ip + ":" + mcast_port, "--local-address", ip,
        "-P", "analyze", "-O", "drop"
    ], stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", required=True)
    parser.add_argument("--ip", required=True)
    parser.add_argument("--mcast_ip", required=True)
    parser.add_argument("--mcast_port", required=True)
    parser.add_argument("--pcap", required=True)
    parser.add_argument("--igmp_log", required=True)
    parser.add_argument("--smcrouted_log", required=True)
    parser.add_argument("--tsp_log", required=True)
    parser.add_argument("--duration", type=int, required=True)
    args = parser.parse_args()

    procs: List[Popen[bytes]] = []
    procs.append(run_smcrouted(args.smcrouted_log))
    time.sleep(2)
    procs.append(run_tcpdump_igmp(args.interface, args.igmp_log))
    procs.append(run_tcpdump_udp(args.interface, args.pcap, args.mcast_ip, args.mcast_port))
    time.sleep(1)
    procs.append(run_tsp(args.ip, args.tsp_log, args.mcast_ip, args.mcast_port))

    time.sleep(args.duration)
    for proc in procs:
        if proc.args[0] == "sudo": # type: ignore
            # tcpdump processes launched in a group
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        else:
            proc.terminate()

    for proc in procs:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if proc.args[0] == "sudo": # type: ignore
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                proc.kill()

if __name__ == "__main__":
    main()
