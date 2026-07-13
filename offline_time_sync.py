#!/usr/bin/env python3
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from email.utils import parsedate_to_datetime


def log(msg):
    print(f"[*] {msg}", flush=True)


def get_gateway_ip():
    """
    Get the default gateway IP (local Router/AP IP) from /proc/net/route.
    Very reliable on Linux/Raspberry Pi systems.
    """
    try:
        if os.path.exists("/proc/net/route"):
            with open("/proc/net/route", "r") as f:
                for line in f:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == "00000000":  # Default route
                        val = fields[2]
                        # Convert little-endian hex value to IP string format
                        parts = [int(val[i : i + 2], 16) for i in (6, 4, 2, 0)]
                        return ".".join(map(str, parts))
    except Exception as e:
        log(f"Failed to detect Gateway IP: {e}")
    return None


def sync_system_time(epoch):
    """
    Set RPi system time and sync to Hardware Clock (RTC).
    """
    try:
        # Temporarily disable system NTP to avoid conflicts
        subprocess.run(["sudo", "timedatectl", "set-ntp", "false"], capture_output=True)

        # Set date from epoch
        res = subprocess.run(
            ["sudo", "date", "-s", f"@{epoch}"], capture_output=True, text=True
        )
        if res.returncode == 0:
            # Sync to RTC (Hardware Clock) if present
            subprocess.run(["sudo", "hwclock", "-w"], capture_output=True)
            log(f"System time successfully synced to: {time.ctime(epoch)}")
            return True
        else:
            log(f"Failed to set date: {res.stderr.strip()}")
    except Exception as e:
        log(f"Error during time sync: {e}")
    return False


def try_gateway_ntp(gateway_ip):
    """
    Try to fetch time using NTP protocol (port 123) from Gateway (Router/AP).
    Many local Wi-Fi routers run an NTP server by default.
    """
    log(f"Attempting NTP query to Gateway: {gateway_ip} (Port 123)...")
    packet = bytearray(48)
    packet[0] = 0x1B  # LI=0, VN=3, Mode=3 (client)

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(2.0)  # Quick 2-second timeout
        client.sendto(packet, (gateway_ip, 123))
        data, address = client.recvfrom(48)
        if data:
            seconds_since_1900 = struct.unpack("!12I", data)[10]
            unix_time = seconds_since_1900 - 2208988800
            log("NTP response received from Gateway!")
            return unix_time
    except Exception as e:
        log(f"Gateway NTP method did not respond: {e}")
    return None


def try_gateway_http_date(gateway_ip):
    """
    Try to fetch 'Date' HTTP header from Gateway admin page (Router/AP).
    Almost all portable Wi-Fi routers run a web admin server on port 80/443.
    We can steal the router's internal time from that HTTP Date header.
    """
    ports = [80, 443, 8080, 8081]
    log(f"Attempting to fetch HTTP Date from Gateway: {gateway_ip}...")

    for port in ports:
        try:
            scheme = "https" if port == 443 else "http"
            url = f"{scheme}://{gateway_ip}:{port}"
            # Send a fast HEAD request (only fetch response headers)
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                date_str = response.headers.get("Date")
                if date_str:
                    dt = parsedate_to_datetime(date_str)
                    epoch = int(dt.timestamp())
                    log(f"HTTP Date header found on port {port}: {date_str}")
                    return epoch
        except Exception:
            continue
    log("Did not find HTTP Date header on Gateway.")
    return None


def main():
    if os.getuid() != 0:
        log("Error: This script must be run as root (sudo).")
        sys.exit(1)

    gateway_ip = get_gateway_ip()
    if not gateway_ip:
        log("Gateway IP not detected (RPi not connected to Wi-Fi).")
        sys.exit(1)

    log(f"Local Gateway IP detected: {gateway_ip}")

    # 1. Try NTP query to Gateway
    epoch = try_gateway_ntp(gateway_ip)
    if epoch:
        if sync_system_time(epoch):
            sys.exit(0)

    # 2. Try fetching HTTP Date from Gateway (Router Admin Page)
    epoch = try_gateway_http_date(gateway_ip)
    if epoch:
        if sync_system_time(epoch):
            sys.exit(0)

    log("All automatic gateway time sync methods failed.")
    sys.exit(1)


if __name__ == "__main__":
    main()
