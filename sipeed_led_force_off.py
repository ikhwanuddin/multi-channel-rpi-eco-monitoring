#!/usr/bin/env python3
"""Experimental hard-off utility for Sipeed MicArray LED ring."""

import argparse
import sys
import time

import serial


def build_sk9822_off_frame(led_count: int) -> bytes:
    frame = bytearray(b"\x00\x00\x00\x00")
    for _ in range(led_count):
        frame.extend((0xE0, 0x00, 0x00, 0x00))
    frame.extend(b"\xFF\xFF\xFF\xFF")
    return bytes(frame)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Try to force all Sipeed MicArray ring LEDs off by sending the "
            "standard commands followed by a raw SK9822-style blackout frame."
        )
    )
    parser.add_argument("--device", default="/dev/ttyACM0", help="CDC ACM device path")
    parser.add_argument("--baud-rate", type=int, default=9600, help="Serial baud rate")
    parser.add_argument("--led-count", type=int, default=12, help="Number of ring LEDs")
    parser.add_argument("--settle-delay", type=float, default=0.3, help="Delay between writes in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frame = build_sk9822_off_frame(args.led_count)

    try:
        with serial.Serial(args.device, baudrate=args.baud_rate, timeout=2) as connection:
            time.sleep(args.settle_delay)
            connection.write(b"f")
            connection.flush()
            time.sleep(args.settle_delay)
            connection.write(b"e")
            connection.flush()
            time.sleep(args.settle_delay)
            connection.write(frame)
            connection.flush()
    except serial.SerialException as exc:
        print(f"ERROR: could not write to {args.device}: {exc}", file=sys.stderr)
        return 1

    print(f"Sent {len(frame)} raw bytes to {args.device}")
    print("If the remaining red ring LED was firmware-controlled via serial passthrough, it should now be off.")
    print("If nothing changes, that LED is likely not exposed as raw SK9822 control over CDC ACM.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())