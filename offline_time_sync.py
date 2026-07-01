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
    Mendapatkan IP default gateway (IP Router/Access Point lokal) dari /proc/net/route.
    Sangat andal pada sistem Linux/Raspberry Pi.
    """
    try:
        if os.path.exists("/proc/net/route"):
            with open("/proc/net/route", "r") as f:
                for line in f:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == "00000000":  # Default route
                        val = fields[2]
                        # Mengonversi nilai hex little-endian ke format IP string
                        parts = [int(val[i : i + 2], 16) for i in (6, 4, 2, 0)]
                        return ".".join(map(str, parts))
    except Exception as e:
        log(f"Gagal mendeteksi Gateway IP: {e}")
    return None


def sync_system_time(epoch):
    """
    Mengatur waktu sistem RPi dan menyinkronkannya ke Hardware Clock (RTC).
    """
    try:
        # Nonaktifkan NTP bawaan sistem sementara agar tidak bentrok
        subprocess.run(["sudo", "timedatectl", "set-ntp", "false"], capture_output=True)

        # Set date dari epoch
        res = subprocess.run(
            ["sudo", "date", "-s", f"@{epoch}"], capture_output=True, text=True
        )
        if res.returncode == 0:
            # Sinkronkan ke RTC (Hardware Clock) jika terpasang
            subprocess.run(["sudo", "hwclock", "-w"], capture_output=True)
            log(f"Waktu sistem sukses disinkronkan ke: {time.ctime(epoch)}")
            return True
        else:
            log(f"Gagal menyetel date: {res.stderr.strip()}")
    except Exception as e:
        log(f"Error saat sinkronisasi waktu: {e}")
    return False


def try_gateway_ntp(gateway_ip):
    """
    Mencoba mengambil waktu menggunakan protokol NTP (port 123) dari Gateway (Router/AP).
    Banyak router Wi-Fi lokal menjalankan NTP server secara default.
    """
    log(f"Mencoba kueri NTP ke Gateway: {gateway_ip} (Port 123)...")
    packet = bytearray(48)
    packet[0] = 0x1B  # LI=0, VN=3, Mode=3 (client)

    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(2.0)  # Timeout cepat 2 detik
        client.sendto(packet, (gateway_ip, 123))
        data, address = client.recvfrom(48)
        if data:
            seconds_since_1900 = struct.unpack("!12I", data)[10]
            unix_time = seconds_since_1900 - 2208988800
            log("Respons NTP diterima dari Gateway!")
            return unix_time
    except Exception as e:
        log(f"Metode NTP Gateway tidak merespons: {e}")
    return None


def try_gateway_http_date(gateway_ip):
    """
    Mencoba mengambil header HTTP 'Date' dari halaman admin Gateway (Router/AP).
    Hampir seluruh router Wi-Fi portabel menjalankan server admin web di port 80/443.
    Kita bisa mencuri waktu internal router dari header Date HTTP tersebut.
    """
    ports = [80, 443, 8080, 8081]
    log(f"Mencoba mengambil HTTP Date dari Gateway: {gateway_ip}...")

    for port in ports:
        try:
            scheme = "https" if port == 443 else "http"
            url = f"{scheme}://{gateway_ip}:{port}"
            # Kirim request HEAD yang sangat cepat (hanya mengambil header respons saja)
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                date_str = response.headers.get("Date")
                if date_str:
                    dt = parsedate_to_datetime(date_str)
                    epoch = int(dt.timestamp())
                    log(f"Header Date HTTP ditemukan di port {port}: {date_str}")
                    return epoch
        except Exception:
            continue
    log("Tidak menemukan header HTTP Date pada Gateway.")
    return None


def main():
    if os.getuid() != 0:
        log("Error: Script ini harus dijalankan sebagai root (sudo).")
        sys.exit(1)

    gateway_ip = get_gateway_ip()
    if not gateway_ip:
        log("Tidak terdeteksi IP Gateway (RPi tidak terhubung ke jaringan Wi-Fi).")
        sys.exit(1)

    log(f"Terdeteksi IP Gateway lokal: {gateway_ip}")

    # 1. Coba kueri NTP ke Gateway
    epoch = try_gateway_ntp(gateway_ip)
    if epoch:
        if sync_system_time(epoch):
            sys.exit(0)

    # 2. Coba ambil HTTP Date dari Gateway (Router Admin Page)
    epoch = try_gateway_http_date(gateway_ip)
    if epoch:
        if sync_system_time(epoch):
            sys.exit(0)

    log("Semua metode sinkronisasi otomatis ke Gateway gagal.")
    sys.exit(1)


if __name__ == "__main__":
    main()
