import os
import signal
import subprocess
import argparse
import time
from subprocess import Popen
from typing import List

def run_ffmpeg(ip: str, mcast_ip: str, mcast_port:str) -> Popen[bytes]:
    return subprocess.Popen([
        "ffmpeg", "-re", "-f", "lavfi", "-i", "testsrc=size=1920x1080:rate=25",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-b:v", "8M", "-maxrate", "8M", "-bufsize", "8M", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-ar", "48000",
        "-muxrate", "8500000", "-mpegts_flags", "+resend_headers", "-f", "mpegts",
        f"udp://{mcast_ip}:{mcast_port}?pkt_size=1316&ttl=1&localaddr={ip}"
    ])

def run_tcpdump(interface: str, mcast_ip: str, mcast_port: str, out_file: str) -> Popen[bytes]:
    return subprocess.Popen([
        "sudo", "tcpdump", "-i", interface, "-n", "-s", "0",
        "udp", "and", "dst", "host", mcast_ip, "and", "dst", "port", mcast_port,
        "-w", out_file
    ], preexec_fn=os.setsid)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", required=True)
    parser.add_argument("--ip", required=True)
    parser.add_argument("--pcap", required=True)
    parser.add_argument("--duration", type=int, required=True)
    args = parser.parse_args()

    procs: List[Popen[bytes]] = []
    procs.append(run_ffmpeg(args.ip, args.mcast_ip, args.mcast_port))
    time.sleep(2)
    procs.append(run_tcpdump(args.interface, args.mcast_ip, args.mcast_port, args.pcap))

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
