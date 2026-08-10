#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive installer & configurator for multi-channel Raspberry Pi
ecosystem monitoring.

This is the single entry point for deploying a monitoring unit. It
replaces the former setup_config.py and now also integrates systemd
service installation and GPIO shutdown-button configuration under one
menu-driven umbrella.

Capabilities (menu):
  1. Generate config.json  (sensor + system + cloud settings)
  2. Install the systemd service (eco-monitor.service)
  3. Configure the GPIO shutdown button (dtoverlay gpio-shutdown)
  4. Install shell shortcuts
  5. Full guided setup
  6-7. Migrations
  8. Show current status
  9. Enable / manage field WiFi timer (power saving)

Run with root privileges -- file-system changes (writing to
/etc/systemd/system/, /boot/config.txt, /etc/profile) require it:

    sudo python3 installer.py
"""

import inspect
import json
import os
import shutil
import subprocess
import sys

# Ensure the repository directory is importable when run via sudo from
# an arbitrary working directory.
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

import sensors

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CONFIG_FILE = os.path.join(REPO_DIR, "config.json")
SERVICE_NAME = "eco-monitor.service"
SERVICE_TEMPLATE = os.path.join(REPO_DIR, SERVICE_NAME)
SERVICE_TARGET = os.path.join("/etc/systemd/system", SERVICE_NAME)
DEFAULT_SERVICE_USER = "pi"

# Field WiFi timer — keep-alive while wlan linked; soft-sleep after no-link grace.
WIFI_TIMER_SERVICE_NAME = "wifi-field-timer.service"
WIFI_TIMER_SCRIPT = os.path.join(REPO_DIR, "wifi_field_timer.sh")
WIFI_TIMER_TEMPLATE = os.path.join(REPO_DIR, WIFI_TIMER_SERVICE_NAME)
WIFI_TIMER_TARGET = os.path.join("/etc/systemd/system", WIFI_TIMER_SERVICE_NAME)
# Seconds without wlan link before soft-sleep (from boot, or after link drops).
WIFI_TIMER_NO_LINK_GRACE_SECONDS = 1200
WIFI_TIMER_CHECK_INTERVAL = 30

MENU_ITEMS = [
    ("1", "Configure sensor & generate config.json", "configure_sensor_and_config"),
    ("2", "Install systemd service (eco-monitor.service)", "install_service"),
    ("3", "Configure GPIO shutdown button", "configure_gpio"),
    (
        "4",
        "Install shell shortcuts (monitor, restarteco, ...)",
        "install_shell_monitor_alias",
    ),
    ("5", "Full setup (1 -> 2 -> 3 -> 4, recommended)", "full_setup"),
    ("6", "Migrate from legacy /etc/profile startup", "migrate_legacy_profile"),
    (
        "7",
        "Migrate config.json to latest schema (remove has_internet, rename offline_mode)",
        "migrate_config_json",
    ),
    ("8", "Show current status", "show_status"),
    (
        "9",
        "Enable / manage field WiFi timer (sleep {}s after wlan lost)".format(
            WIFI_TIMER_NO_LINK_GRACE_SECONDS
        ),
        "manage_wifi_field_timer",
    ),
    ("10", "Exit", None),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_real_user():
    """Return the non-root user who invoked sudo, falling back to 'pi'."""
    user = os.environ.get("SUDO_USER") or os.environ.get("USER")
    if user and user != "root":
        return user
    return DEFAULT_SERVICE_USER


def ensure_root():
    """Abort if not running as root."""
    if os.geteuid() != 0:
        print("ERROR: this installer must be run as root.")
        print("       Use:  sudo python3 installer.py")
        sys.exit(1)


def run_cmd(cmd, check=False, capture=False, timeout=30):
    """Run a command list, optionally checking the return code / capturing output."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=True,
            timeout=timeout,
        )
        if check and result.returncode != 0:
            print("Command failed: {}".format(" ".join(cmd)))
            if capture and result.stderr:
                print("  stderr: {}".format(result.stderr.strip()))
        return result
    except subprocess.TimeoutExpired:
        print("Command timed out: {}".format(" ".join(cmd)))
        return None
    except FileNotFoundError:
        print("Command not found: {}".format(cmd[0]))
        return None


def fix_ownership(path):
    """Restore ownership of *path* to the real (non-root) user."""
    user = get_real_user()
    try:
        grp = run_cmd(["id", "-gn", user], capture=True, timeout=5)
        group = grp.stdout.strip() if grp and grp.stdout else user
    except Exception:
        group = user
    try:
        subprocess.run(["chown", "{}:{}".format(user, group), path], timeout=5)
        print("Ownership of {} restored to {}:{}".format(path, user, group))
    except Exception as e:
        print("WARNING: could not fix ownership of {}: {}".format(path, e))


def find_boot_config():
    """Return the boot config.txt path, or None if not found."""
    for candidate in ["/boot/firmware/config.txt", "/boot/config.txt"]:
        if os.path.isfile(candidate):
            return candidate
    return None


def load_config():
    """Load config.json, returning None if it does not exist or is invalid."""
    if not os.path.isfile(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print("WARNING: could not parse {}: {}".format(CONFIG_FILE, e))
        return None


def save_config(config):
    """Write config dict to config.json and fix ownership to the real user."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
        f.write("\n")
    fix_ownership(CONFIG_FILE)


def pause():
    """Wait for the user to press Enter before returning to the menu."""
    print()
    try:
        input("Press Enter to return to the menu ...")
    except EOFError:
        pass


def ask_yes_no(prompt, default="n"):
    """Ask a yes/no question, returning True for yes."""
    choice = {}
    config_parse(
        {
            "prompt": prompt,
            "default": default,
            "type": str,
            "name": "answer",
            "valid": ["y", "n"],
        },
        choice,
    )
    return choice["answer"] == "y"


# ---------------------------------------------------------------------------
# config_parse -- validated interactive input (preserved from setup_config.py)
# ---------------------------------------------------------------------------
def config_parse(opt, cnfg):
    """
    Parse a config option (dictionary with name, prompt, type, optional
    default, optional list of valid values), validate it and append the
    choice to an existing config dictionary.

    Parameters:
        opt: A config option dictionary.
        cnfg: The config dictionary to extend.
    """

    if "default" in opt.keys():
        opt["dft_str"] = "\nPress return to accept default value [{}]".format(
            opt["default"]
        )
    else:
        opt["dft_str"] = ""

    if "valid" in opt.keys():
        opt["vld_str"] = ", valid options: "
        vld_opts = ", ".join([str(vl) for vl in opt["valid"]])
        opt["vld_str"] += vld_opts
    else:
        opt["vld_str"] = ""

    valid_choice = False
    target_type = opt["type"]

    print("{prompt} [{name}{vld_str}]{dft_str}".format(**opt))

    while not valid_choice:
        # Python 2 input() evaluates input as code and breaks on empty Enter.
        # Use raw_input() on Python 2 and input() on Python 3.
        try:
            input_func = raw_input
        except NameError:
            input_func = input

        try:
            value = input_func()
        except EOFError:
            print("Input stream ended unexpectedly. Please try again.")
            continue

        try:
            # check for input and handle defaults
            if value == "" and "default" in opt.keys():
                value = opt["default"]
                valid_choice = True
            elif value == "" and "default" not in opt.keys():
                print("No value entered and no default value is set")
                continue

            # need to be a little careful here in parsing raw inputs because
            # bool() convert anything but an empty string to True, so handle
            # those differently
            if target_type.__name__ == "bool" and not isinstance(value, bool):
                if value.lower() in ["t", "true"]:
                    value = True
                    valid_choice = True
                elif value.lower() in ["f", "false"]:
                    value = False
                    valid_choice = True
                else:
                    print("Value not recognized as true or false")
                    continue
            else:
                try:
                    value = target_type(value)
                except ValueError:
                    print(
                        'Value "{}" cannot be converted to type {}'.format(
                            value, target_type.__name__
                        )
                    )
                    continue

            # check if entries appear in the list of valid options, if there is one
            if "valid" in opt.keys() and value not in opt["valid"]:
                print("Value not in {}".format(vld_opts))
            else:
                valid_choice = True
                cnfg[opt["name"]] = value
        except (ValueError, AttributeError):
            print("Unable to validate entered value. Please try again.")


# ---------------------------------------------------------------------------
# Menu action 1: configure sensor & generate config.json
# ---------------------------------------------------------------------------
def configure_sensor_and_config():
    """Interactive configuration: generate config.json from user input."""

    if os.path.exists(CONFIG_FILE):
        if not ask_yes_no("Config file already exists. Replace?", "n"):
            print("Leaving existing config unchanged.")
            return
        os.remove(CONFIG_FILE)

    # Get available sensor classes (ignore the base class).
    sensor_classes = inspect.getmembers(sensors, inspect.isclass)
    sensor_classes = [sc for sc in sensor_classes if sc[0] != "SensorBase"]
    sensor_numbers = [idx + 1 for idx in range(len(sensor_classes))]
    sensor_options = {nm: tp for nm, tp in zip(sensor_numbers, sensor_classes)}
    sensor_menu = [str(ky) + ": " + tp[0] for ky, tp in sensor_options.items()]

    sensor_prompt = (
        "Hello! Follow these instructions to perform a one-off set up of your "
        "ecosystem monitoring unit\nFirst lets do the sensor setup. Select one "
        "of the following available sensor types:\n"
    )
    sensor_prompt += "\n".join(sensor_menu) + "\n"

    sensor_config = {}
    config_parse(
        {
            "prompt": sensor_prompt,
            "valid": sensor_numbers,
            "type": int,
            "name": "sensor_index",
        },
        sensor_config,
    )

    sensor_config["sensor_type"] = sensor_options[sensor_config["sensor_index"]][0]
    sensor_config_options = sensor_options[sensor_config["sensor_index"]][1].options()

    for option in sensor_config_options:
        config_parse(option, sensor_config)

    # upload_enabled is True by default.
    # Record() will create an upload sync thread when True;
    # actual upload fires only when internet is reachable at runtime.
    upload_config = {"upload_enabled": True}

    deployment_info_options = [
        {
            "name": "test_mode",
            "type": int,
            "prompt": (
                "Enable test mode?\n"
                "1 = Yes (forces recording even if internet is available, skips all uploads)\n"
                "0 = No (standard behavior)"
            ),
            "default": 0,
            "valid": [0, 1],
        },
    ]

    deployment_config = {}
    for option in deployment_info_options:
        config_parse(option, deployment_config)

    _configure_cloud_and_system(sensor_config, upload_config, deployment_config)


def _configure_cloud_and_system(sensor_config, upload_config, deployment_config):
    """Collect rclone, gist, and system config, then save config.json."""

    # rclone config
    rclone_config = {}
    rclone_config_options = [
        {
            "name": "remote_name",
            "type": str,
            "prompt": "Optional: enter rclone remote name (e.g., mybox, gdrive). Leave blank to use script default.",
            "default": "mybox",
        },
        {
            "name": "config_path",
            "type": str,
            "prompt": "Optional: enter full rclone config path. Leave blank to use default rclone config lookup.",
            "default": "/home/pi/.config/rclone/rclone.conf",
        },
        {
            "name": "target_path",
            "type": str,
            "prompt": "Optional: enter remote folder path for uploads (shared folder on Box).",
            "default": "monitoring_data",
        },
    ]

    print("\nNow let's do the optional rclone cloud storage details...")
    for option in rclone_config_options:
        config_parse(option, rclone_config)

    # GitHub Gist config for shared rclone.conf sync
    gist_config = {
        "enabled": 0,
        "github_token": "",
        "gist_id": "",
        "filename": "rclone.conf",
    }
    gist_config_options = [
        {
            "name": "enabled",
            "type": int,
            "prompt": (
                "Enable rclone.conf sync via private GitHub Gist?\n"
                "1 = Yes (recommended for multi-RPi token sharing)\n"
                "0 = No"
            ),
            "default": 1,
            "valid": [0, 1],
        },
        {
            "name": "github_token",
            "type": str,
            "prompt": "GitHub token for Gist API access (required if enabled).",
            "default": "",
        },
        {
            "name": "gist_id",
            "type": str,
            "prompt": "Private Gist ID that stores rclone.conf (required if enabled).",
            "default": "",
        },
        {
            "name": "filename",
            "type": str,
            "prompt": "Filename inside the Gist for rclone config.",
            "default": "rclone.conf",
        },
    ]

    print("\nNow let's do the optional GitHub Gist sync details...")
    config_parse(gist_config_options[0], gist_config)

    if gist_config["enabled"] == 1:
        for option in gist_config_options[1:]:
            config_parse(option, gist_config)
        while gist_config["github_token"].strip() == "":
            print("github_token cannot be empty when gist sync is enabled.")
            config_parse(gist_config_options[1], gist_config)
        while gist_config["gist_id"].strip() == "":
            print("gist_id cannot be empty when gist sync is enabled.")
            config_parse(gist_config_options[2], gist_config)

    # System config options
    sys_config_options = [
        {
            "name": "working_dir",
            "type": str,
            "prompt": "Enter the working directory path",
            "default": "/home/pi/tmp_dir",
        },
        {
            "name": "upload_dir",
            "type": str,
            "prompt": "Enter the upload directory path",
            "default": "/home/pi/monitoring_data",
        },
        {
            "name": "reboot_time",
            "type": str,
            "prompt": "Enter the primary time for the daily reboot",
            "default": "02:00",
        },
        {
            "name": "reboot_time_2",
            "type": str,
            "prompt": "Enter an optional second daily reboot time (HH:MM), or leave blank to disable",
            "default": "",
        },
    ]

    sensor_type_name = sensor_config["sensor_type"]
    if sensor_type_name.startswith("Sipeed"):
        shutdown_pin_hint = "21"
    elif sensor_type_name.startswith("Respeaker"):
        shutdown_pin_hint = "26"
    else:
        shutdown_pin_hint = "see ADVANCED_CONFIGURATION.md"

    sys_config_options.append(
        {
            "name": "use_system_shutdown_button",
            "type": int,
            "prompt": (
                "Use system-wide shutdown button handling (dtoverlay gpio-shutdown) "
                "instead of Python GPIO listener? "
                "Recommended shutdown pin for {} is GPIO {}. "
                "(1 for yes, 0 for no)".format(sensor_type_name, shutdown_pin_hint)
            ),
            "default": 1,
            "valid": [0, 1],
        }
    )

    print("Now let's do the system details...")
    sys_config = {}
    for option in sys_config_options:
        config_parse(option, sys_config)

    config = {
        "rclone": rclone_config,
        "gist": gist_config,
        "upload_enabled": upload_config["upload_enabled"],
        "test_mode": deployment_config["test_mode"],
        "sensor": sensor_config,
        "sys": sys_config,
    }

    save_config(config)
    print("\nconfig.json written to {}".format(CONFIG_FILE))


# ---------------------------------------------------------------------------
# Menu action 2: install systemd service
# ---------------------------------------------------------------------------
def install_service():
    """Install eco-monitor.service from the repo template into systemd."""

    if not os.path.isfile(SERVICE_TEMPLATE):
        print("ERROR: service template not found: {}".format(SERVICE_TEMPLATE))
        return

    if not os.path.isfile(CONFIG_FILE):
        print("WARNING: config.json not found. The service will fail to start")
        print("         until you run menu option 1 to generate it.")

    user = get_real_user()

    # Read the template and substitute placeholders.
    with open(SERVICE_TEMPLATE, "r") as f:
        content = f.read()

    content = content.replace("__REPO_DIR__", REPO_DIR)
    content = content.replace("__SERVICE_USER__", user)

    with open(SERVICE_TARGET, "w") as f:
        f.write(content)
    print("Service unit written to {}".format(SERVICE_TARGET))

    # Reload systemd and enable the service.
    print("Reloading systemd daemon...")
    run_cmd(["systemctl", "daemon-reload"], check=True)

    print("Enabling {} (start on boot)...".format(SERVICE_NAME))
    run_cmd(["systemctl", "enable", SERVICE_NAME], check=True)

    # Offer to start immediately.
    if ask_yes_no("\nStart the service now?", "n"):
        print("Starting {} ...".format(SERVICE_NAME))
        run_cmd(["systemctl", "start", SERVICE_NAME], check=True)
        r = run_cmd(["systemctl", "is-active", SERVICE_NAME], capture=True)
        status = r.stdout.strip() if r and r.stdout else "unknown"
        print("Service status: {}".format(status))
    else:
        print("Service enabled but not started. It will start on next boot.")
        print("Start manually with:  sudo systemctl start {}".format(SERVICE_NAME))

    print("\nUseful commands:")
    print("  sudo systemctl status {}".format(SERVICE_NAME))
    print("  sudo journalctl -u {} -f".format(SERVICE_NAME))


# ---------------------------------------------------------------------------
# Menu action 3: configure GPIO shutdown button
# ---------------------------------------------------------------------------
def configure_gpio():
    """Apply dtoverlay=gpio-shutdown and update config.json."""

    boot_config = find_boot_config()
    if boot_config is None:
        print("ERROR: could not find /boot/config.txt or /boot/firmware/config.txt")
        return

    config = load_config()
    if config is None:
        print("ERROR: config.json not found. Run menu option 1 first.")
        return

    sensor_type = config.get("sensor", {}).get("sensor_type", "")
    if sensor_type.startswith("Sipeed"):
        default_pin = 21
    elif sensor_type.startswith("Respeaker"):
        default_pin = 26
    else:
        default_pin = 26

    pin_choice = {}
    config_parse(
        {
            "prompt": (
                "Which GPIO BCM pin is the shutdown button wired to?\n"
                "Sensor detected: {} (recommended pin: GPIO {})".format(
                    sensor_type or "unknown", default_pin
                )
            ),
            "default": default_pin,
            "type": int,
            "name": "gpio_pin",
        },
        pin_choice,
    )
    gpio_pin = pin_choice["gpio_pin"]

    overlay_line = (
        "dtoverlay=gpio-shutdown,gpio_pin={},active_low=1,gpio_pull=up".format(gpio_pin)
    )

    # Read current boot config and remove any existing gpio-shutdown overlay.
    with open(boot_config, "r") as f:
        lines = f.readlines()

    filtered = [
        ln for ln in lines if not ln.strip().startswith("dtoverlay=gpio-shutdown")
    ]
    removed = len(lines) - len(filtered)
    if removed:
        print(
            "Removed {} existing gpio-shutdown line(s) from {}".format(
                removed, boot_config
            )
        )

    # Append the new overlay (ensure the file ends with a newline).
    if filtered and not filtered[-1].endswith("\n"):
        filtered[-1] = filtered[-1] + "\n"
    filtered.append(overlay_line + "\n")

    with open(boot_config, "w") as f:
        f.writelines(filtered)
    print("Added overlay to {}: {}".format(boot_config, overlay_line))

    # Update config.json: set use_system_shutdown_button = 1
    config.setdefault("sys", {})["use_system_shutdown_button"] = 1
    save_config(config)
    print("Updated config.json: sys.use_system_shutdown_button = 1")

    print("\nGPIO shutdown button configured. A REBOOT is required for the")
    print("overlay to take effect.")
    print("  sudo reboot")


# ---------------------------------------------------------------------------
# Menu action 4: install shell monitor alias
# ---------------------------------------------------------------------------
def install_shell_monitor_alias():
    """Add a 'monitor' shell function to the user's .bashrc."""
    user = get_real_user()
    if user == "root":
        bashrc_path = "/root/.bashrc"
    else:
        bashrc_path = os.path.expanduser("~{}/.bashrc".format(user))
        if bashrc_path.startswith("~"):
            bashrc_path = "/home/{}/.bashrc".format(user)

    print("Target .bashrc: {}".format(bashrc_path))

    if not os.path.exists(bashrc_path):
        print(
            "WARNING: Cannot find .bashrc for user '{}' at {}".format(user, bashrc_path)
        )
        if ask_yes_no("Create a new .bashrc?", "y"):
            open(bashrc_path, "a").close()
            fix_ownership(bashrc_path)
        else:
            return

    start_marker = "# ── Eco-monitor shell shortcuts ──"
    end_marker = "# ── end eco-monitor shortcuts ──"
    with open(bashrc_path, "r") as f:
        content = f.read()

    # NOTE: This snippet is written verbatim into .bashrc. Do not use
    # str.format / f-strings here — bash `{` `}` would break substitution.
    snippet = r"""
# ── Eco-monitor shell shortcuts ──
# monitor   : health dashboard + live logs (Ctrl+C to quit)
# healtheco : health dashboard only (no log follow; includes compact device status + readable WiFi line)
# restarteco: daemon-reload + restart eco-monitor
# statuseco : systemctl status eco-monitor
# stopeco   : stop eco-monitor
# starteco  : start eco-monitor
# sizeeco   : disk usage of monitoring folders
#
# Decode vcgencmd get_throttled (hex bitmask):
#   bit 0  (0x1)      under-voltage NOW
#   bit 1  (0x2)      frequency capped NOW
#   bit 2  (0x4)      throttled NOW
#   bit 3  (0x8)      soft temp limit NOW
#   bit 16 (0x10000)  under-voltage has occurred
#   bit 17 (0x20000)  frequency capping has occurred
#   bit 18 (0x40000)  throttling has occurred
#   bit 19 (0x80000)  soft temp limit has occurred

_eco_svc_line() {
    # $1 = unit name
    local u="$1" en act
    en=$(systemctl is-enabled "$u" 2>/dev/null || echo "n/a")
    act=$(systemctl is-active "$u" 2>/dev/null || echo "n/a")
    printf "  %-28s enabled=%-12s active=%s\n" "$u" "$en" "$act"
}

_eco_conn_line() {
    if command -v nmcli >/dev/null 2>&1; then
        echo "  Device status:"
        nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status 2>/dev/null \
            | awk -F: '{printf "    %-12s type=%-9s state=%-11s conn=%s\n", $1, $2, $3, $4}'
    else
        echo "  nmcli: not installed"
    fi
}

_eco_wifi_active_line() {
    if command -v nmcli >/dev/null 2>&1; then
        echo "  WiFi active:"
        local w name
        for w in /sys/class/net/wlan*; do
            [ -e "$w" ] || continue
            name=$(basename "$w")
            nmcli -t -f IN-USE,SSID,MODE,CHAN,RATE,SIGNAL,BARS,SECURITY dev wifi list ifname "$name" 2>/dev/null \
                | awk -F: -v name="$name" '
                    $1 == "*" {
                        print sprintf("    %-12s SSID=%s  mode=%s  ch=%s  rate=%s  signal=%s%%  bars=%s  sec=%s", \
                            name, $2, $3, $4, $5, $6, $7, $8)
                        found=1
                        exit
                    }
                    END {
                        if (!found) {
                            print sprintf("    %-12s (no active WiFi details)", name)
                        }
                    }
                '
        done
    fi
}

_eco_decode_throttled() {
    # $1 = raw hex from vcgencmd (e.g. throttled=0x50005)
    local raw="$1" hex val
    hex=$(echo "$raw" | sed -n 's/.*throttled=\(0x[0-9a-fA-F]*\).*/\1/p')
    [ -z "$hex" ] && hex=$(echo "$raw" | grep -oE '0x[0-9a-fA-F]+' | head -1)
    [ -z "$hex" ] && { echo "  (could not parse throttled value: $raw)"; return; }
    # shellcheck disable=SC2003
    val=$((hex))
    printf "  raw: %s (%s)\n" "$hex" "$raw"
    if [ "$val" -eq 0 ]; then
        echo "  OK — no under-voltage / throttle flags"
        return
    fi
    echo "  FLAGS (NOW / history):"
    [ $((val & 0x1)) -ne 0 ]      && echo "    !! UNDER-VOLTAGE right now"
    [ $((val & 0x2)) -ne 0 ]      && echo "    !! ARM frequency capped right now"
    [ $((val & 0x4)) -ne 0 ]      && echo "    !! throttled right now"
    [ $((val & 0x8)) -ne 0 ]      && echo "    !! soft temp limit right now"
    [ $((val & 0x10000)) -ne 0 ]  && echo "    -- under-voltage HAS occurred since boot"
    [ $((val & 0x20000)) -ne 0 ]  && echo "    -- frequency capping HAS occurred since boot"
    [ $((val & 0x40000)) -ne 0 ]  && echo "    -- throttling HAS occurred since boot"
    [ $((val & 0x80000)) -ne 0 ]  && echo "    -- soft temp limit HAS occurred since boot"
}

healtheco() {
    echo "============================================================"
    echo "  MAARU health snapshot  $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo "============================================================"

    echo ""
    echo "--- Host ---"
    if [ -r /proc/device-tree/model ]; then
        printf "  Model:  "; tr -d '\0' </proc/device-tree/model; echo
    fi
    printf "  Uptime: "; uptime -p 2>/dev/null || uptime
    printf "  Load:   "; cut -d' ' -f1-3 /proc/loadavg 2>/dev/null; echo

    echo ""
    echo "--- Services ---"
    _eco_svc_line eco-monitor.service
    _eco_svc_line wifi-field-timer.service

    echo ""
    echo "--- Connection status ---"
    _eco_conn_line
    _eco_wifi_active_line

    echo ""
    echo "--- WiFi / radio ---"
    if command -v rfkill >/dev/null 2>&1; then
        rfkill list 2>/dev/null | sed 's/^/  /' || echo "  rfkill: (none)"
    else
        echo "  rfkill: not installed"
    fi
    local w found=0
    for w in /sys/class/net/wlan*; do
        [ -e "$w" ] || continue
        found=1
        local name state
        name=$(basename "$w")
        state=$(cat "$w/operstate" 2>/dev/null || echo "?")
        printf "  %s: operstate=%s" "$name" "$state"
        ip -4 -o addr show dev "$name" scope global 2>/dev/null \
            | awk '{print "  ip="$4}' | tr '\n' ' '
        echo
    done
    if [ "$found" -eq 0 ]; then
        echo "  No wlan* interface (dongle missing, driver down, or rfkill blocked)"
    fi
    if ip route show default 2>/dev/null | grep -q .; then
        echo "  Default route:"
        ip route show default 2>/dev/null | sed 's/^/    /'
    else
        echo "  Default route: (none)"
    fi
    if command -v ping >/dev/null 2>&1; then
        if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
            echo "  Internet probe 8.8.8.8: OK"
        else
            echo "  Internet probe 8.8.8.8: FAIL (offline or blocked)"
        fi
    fi

    echo ""
    echo "--- Power / throttle (vcgencmd) ---"
    if command -v vcgencmd >/dev/null 2>&1; then
        local thr
        thr=$(vcgencmd get_throttled 2>/dev/null || echo "error")
        _eco_decode_throttled "$thr"
        # Extra sensors when available
        vcgencmd measure_volts 2>/dev/null | sed 's/^/  /' || true
        vcgencmd measure_temp 2>/dev/null | sed 's/^/  /' || true
    else
        echo "  vcgencmd not found (not a Pi firmware image?)"
    fi

    echo ""
    echo "--- Disk ---"
    df -h / /home 2>/dev/null | sed 's/^/  /' || df -h / | sed 's/^/  /'
    du -sh /home/pi/monitoring_data/live_data/ /home/pi/tmp_dir/ /home/pi/pre_upload_dir/ 2>/dev/null \
        | sed 's/^/  /' || true

    echo ""
    echo "--- Recent kernel issues (dmesg, last matches) ---"
    if dmesg -T 2>/dev/null | grep -iE 'under-voltage|throttl|Over-voltage|Voltage' | tail -n 8 | sed 's/^/  /' | grep -q .; then
        dmesg -T 2>/dev/null | grep -iE 'under-voltage|throttl|Over-voltage|Voltage' | tail -n 8 | sed 's/^/  /'
    else
        # BusyBox / old dmesg without -T
        if dmesg 2>/dev/null | grep -iE 'under-voltage|throttl' | tail -n 8 | sed 's/^/  /' | grep -q .; then
            dmesg 2>/dev/null | grep -iE 'under-voltage|throttl' | tail -n 8 | sed 's/^/  /'
        else
            echo "  (no under-voltage/throttle lines in dmesg ring buffer)"
        fi
    fi
    echo "  USB / storage (last matches):"
    if dmesg -T 2>/dev/null | grep -iE 'usb .*disconnect|USB disconnect|I/O error|mmcblk|Buffer I/O|reset SuperSpeed|error -71|error -32' | tail -n 6 | sed 's/^/  /' | grep -q .; then
        dmesg -T 2>/dev/null | grep -iE 'usb .*disconnect|USB disconnect|I/O error|mmcblk|Buffer I/O|reset SuperSpeed|error -71|error -32' | tail -n 6 | sed 's/^/    /'
    else
        dmesg 2>/dev/null | grep -iE 'usb .*disconnect|USB disconnect|I/O error|mmcblk|Buffer I/O' | tail -n 6 | sed 's/^/    /' \
            || echo "    (none)"
    fi

    echo ""
    echo "--- Recent service log errors (eco-monitor + wifi-field-timer) ---"
    journalctl -u eco-monitor.service -u wifi-field-timer.service -p warning..alert -n 12 --no-pager 2>/dev/null \
        | sed 's/^/  /' || echo "  (journalctl unavailable)"

    echo "============================================================"
}

monitor() {
    healtheco
    echo ""
    echo "--- Live logs: eco-monitor + wifi-field-timer (Ctrl+C to quit) ---"
    echo "    (health snapshot above; logs follow below)"
    sudo journalctl -u eco-monitor.service -u wifi-field-timer.service -f --no-hostname
}

sizeeco() {
    echo "--- Ukuran direktori eco-monitor ---"
    du -sh /home/pi/monitoring_data/live_data/ /home/pi/tmp_dir/ /home/pi/pre_upload_dir/ 2>/dev/null
}

alias restarteco='sudo systemctl daemon-reload && sudo systemctl restart eco-monitor.service'
alias statuseco='sudo systemctl status eco-monitor.service wifi-field-timer.service'
alias stopeco='sudo systemctl stop eco-monitor.service'
alias starteco='sudo systemctl start eco-monitor.service'
# ── end eco-monitor shortcuts ──
"""

    if start_marker in content:
        if end_marker in content:
            print("Updating existing shell shortcuts in {}...".format(bashrc_path))
            start_idx = content.find(start_marker)
            end_idx = content.find(end_marker) + len(end_marker)
            new_content = content[:start_idx] + snippet.strip() + content[end_idx:]
            with open(bashrc_path, "w") as f:
                f.write(new_content)
        else:
            print("Shell shortcuts start marker found, but end marker is missing.")
            print("Appending new shortcuts to {} instead.".format(bashrc_path))
            with open(bashrc_path, "a") as f:
                f.write("\n" + snippet.strip() + "\n")
    else:
        with open(bashrc_path, "a") as f:
            f.write("\n" + snippet.strip() + "\n")

    fix_ownership(bashrc_path)

    print("Successfully installed/updated shell shortcuts in {}".format(bashrc_path))
    print(
        "Shortcuts installed: monitor, healtheco, restarteco, statuseco, "
        "stopeco, starteco, sizeeco"
    )
    print("  monitor   = health dashboard (compact device status + readable WiFi line, WiFi, throttle, services, disk) + live logs")
    print("  healtheco = health dashboard only (no log follow; includes compact device status + readable WiFi line)")
    print("To use them immediately, run: source {}".format(bashrc_path))
    print("Or simply log out and log back in.")


# ---------------------------------------------------------------------------
# Menu action 5: full guided setup
# ---------------------------------------------------------------------------
def full_setup():
    """Run the complete guided setup: config -> service -> GPIO -> monitor alias."""
    print("=" * 60)
    print("  FULL GUIDED SETUP")
    print("=" * 60)

    print("\n--- Step 1 of 5: Configure sensor & generate config.json ---")
    configure_sensor_and_config()

    print("\n--- Step 2 of 5: Install systemd service ---")
    install_service()

    print("\n--- Step 3 of 5: Configure GPIO shutdown button ---")
    if ask_yes_no("Configure the GPIO shutdown button now?", "y"):
        configure_gpio()
    else:
        print("Skipping GPIO configuration. You can do it later via menu option 3.")

    print("\n--- Step 4 of 5: Install shell shortcuts ---")
    if ask_yes_no(
        "Install shell shortcuts (monitor, restarteco, ...) to .bashrc?", "y"
    ):
        install_shell_monitor_alias()
    else:
        print("Skipping shell shortcuts installation.")

    print("\n--- Step 5 of 5: Field WiFi timer (power saving) ---")
    print("WiFi stays on while wlan is linked (home/remote OK).")
    print(
        "After wlan is gone for {}s ({} min), soft-sleep until reboot.".format(
            WIFI_TIMER_NO_LINK_GRACE_SECONDS,
            WIFI_TIMER_NO_LINK_GRACE_SECONDS // 60,
        )
    )
    print("(wlan down only — no persistent rfkill / nmcli radio off).")
    if ask_yes_no(
        "Enable field WiFi timer now? (recommended for battery / forest units)",
        "y",
    ):
        enable_wifi_field_timer()
    else:
        print("Skipping WiFi timer. Enable later via menu option 9.")

    print("\n" + "=" * 60)
    print("  Full setup complete!")
    print("=" * 60)
    print("Next steps:")
    print("  1. Reboot to apply the GPIO overlay (if configured):")
    print("       sudo reboot")
    print("  2. After reboot, check the service:")
    print("       sudo systemctl status {}".format(SERVICE_NAME))
    print("     Or simply type `monitor` if you installed the shortcut.")
    print("  3. If WiFi timer enabled: stays on while linked; sleeps {}s after wlan lost:".format(
        WIFI_TIMER_NO_LINK_GRACE_SECONDS
    ))
    print("       sudo systemctl status {}".format(WIFI_TIMER_SERVICE_NAME))


# ---------------------------------------------------------------------------
# Menu action 5: migrate from legacy /etc/profile startup
# ---------------------------------------------------------------------------
def migrate_legacy_profile():
    """Remove the legacy recorder_startup_script.sh lines from /etc/profile."""

    profile_path = "/etc/profile"
    if not os.path.isfile(profile_path):
        print("{} not found, nothing to migrate.".format(profile_path))
        return

    with open(profile_path, "r") as f:
        lines = f.readlines()

    # Identify the two legacy lines:
    #   chmod +x ~/multi-channel-rpi-eco-monitoring/*;
    #   sudo -u pi ~/multi-channel-rpi-eco-monitoring/recorder_startup_script.sh;
    legacy_markers = [
        "recorder_startup_script.sh",
        "chmod +x ~/multi-channel-rpi-eco-monitoring",
    ]

    removed_lines = []
    filtered = []
    for ln in lines:
        if any(marker in ln for marker in legacy_markers):
            removed_lines.append(ln.rstrip("\n"))
        else:
            filtered.append(ln)

    if not removed_lines:
        print("No legacy startup lines found in {}.".format(profile_path))
        print("The system is likely already migrated to systemd.")
        return

    with open(profile_path, "w") as f:
        f.writelines(filtered)

    print("Removed {} legacy line(s) from {}:".format(len(removed_lines), profile_path))
    for ln in removed_lines:
        print("  - {}".format(ln))

    print("\nMigration complete. Now install the systemd service via menu option 2")
    print("if you have not done so already, then reboot:")
    print("  sudo reboot")


# ---------------------------------------------------------------------------
# Menu action 7: migrate config.json to latest schema
# ---------------------------------------------------------------------------
def migrate_config_json():
    """
    Migrate config.json from the legacy schema to the current one.

    Changes applied:
      1. Remove the dead 'has_internet' key if present.
      2. Rename 'offline_mode' (int 0/1) to 'upload_enabled' (bool).
      3. Log a summary of what was changed.
    """
    config = load_config()
    if config is None:
        print("No valid config.json found at {}. Nothing to migrate.".format(CONFIG_FILE))
        return

    changes = []

    # 1. Remove has_internet (dead code)
    if "has_internet" in config:
        del config["has_internet"]
        changes.append("removed 'has_internet' (dead key)")

    # 2. Rename offline_mode -> upload_enabled (invert + convert to bool)
    if "offline_mode" in config:
        old_val = config.pop("offline_mode")
        # offline_mode=1 meant "upload disabled", upload_enabled=True means "upload enabled"
        new_val = old_val == 0
        config["upload_enabled"] = new_val
        changes.append(
            "renamed 'offline_mode' ({}) -> 'upload_enabled' ({})".format(
                old_val, new_val
            )
        )

    # 3. Also check inside the sensor config (passed to continuous_recording)
    sensor = config.get("sensor", {})
    if "offline_mode" in sensor:
        old_val = sensor.pop("offline_mode")
        new_val = old_val == 0
        sensor["upload_enabled"] = new_val
        changes.append(
            "renamed sensor.offline_mode ({}) -> sensor.upload_enabled ({})".format(
                old_val, new_val
            )
        )

    if not changes:
        print("config.json already matches the latest schema. Nothing to do.")
        return

    save_config(config)
    print("config.json migrated. Changes applied:")
    for c in changes:
        print("  - {}".format(c))
    print("\nYou can verify the result with menu option 8 (Show current status).")


# ---------------------------------------------------------------------------
# Menu action 9: field WiFi timer (power saving)
# ---------------------------------------------------------------------------
def _wifi_timer_status_lines():
    """Return human-readable status lines for the field WiFi timer unit."""
    lines = []
    installed = os.path.isfile(WIFI_TIMER_TARGET)
    lines.append("  Unit file installed: {}".format("yes" if installed else "no"))
    if installed:
        lines.append("    Path: {}".format(WIFI_TIMER_TARGET))
        r = run_cmd(
            ["systemctl", "is-enabled", WIFI_TIMER_SERVICE_NAME],
            capture=True,
            timeout=5,
        )
        enabled = r.stdout.strip() if r and r.stdout else "unknown"
        lines.append("  Enabled:             {}".format(enabled))
        r = run_cmd(
            ["systemctl", "is-active", WIFI_TIMER_SERVICE_NAME],
            capture=True,
            timeout=5,
        )
        active = r.stdout.strip() if r and r.stdout else "unknown"
        lines.append("  Active:              {}".format(active))
        # Surface the configured no-link grace if present in the unit file.
        try:
            with open(WIFI_TIMER_TARGET, "r") as f:
                for ln in f:
                    if "NO_LINK_GRACE_SECONDS=" in ln and not ln.strip().startswith("#"):
                        lines.append("  Config line:         {}".format(ln.strip()))
                        break
        except OSError:
            pass
    script_ok = os.path.isfile(WIFI_TIMER_SCRIPT)
    lines.append(
        "  Script present:      {} ({})".format(
            "yes" if script_ok else "no", WIFI_TIMER_SCRIPT
        )
    )
    return lines


def enable_wifi_field_timer():
    """Install unit, enable on boot, and start the field WiFi timer now."""
    if not os.path.isfile(WIFI_TIMER_TEMPLATE):
        print("ERROR: service template not found: {}".format(WIFI_TIMER_TEMPLATE))
        return False
    if not os.path.isfile(WIFI_TIMER_SCRIPT):
        print("ERROR: timer script not found: {}".format(WIFI_TIMER_SCRIPT))
        return False

    # Ensure the script is executable for the service ExecStart.
    try:
        mode = os.stat(WIFI_TIMER_SCRIPT).st_mode
        os.chmod(WIFI_TIMER_SCRIPT, mode | 0o111)
    except OSError as e:
        print("WARNING: could not chmod +x on {}: {}".format(WIFI_TIMER_SCRIPT, e))

    with open(WIFI_TIMER_TEMPLATE, "r") as f:
        content = f.read()

    content = content.replace("__REPO_DIR__", REPO_DIR)
    # Pin installer defaults; drop legacy MAX_ON_SECONDS (old forced-off-while-linked).
    env_block = (
        "Environment=NO_LINK_GRACE_SECONDS={}\n"
        "Environment=CHECK_INTERVAL={}\n".format(
            WIFI_TIMER_NO_LINK_GRACE_SECONDS,
            WIFI_TIMER_CHECK_INTERVAL,
        )
    )
    if (
        "Environment=NO_LINK_GRACE_SECONDS=" in content
        or "Environment=MAX_ON_SECONDS=" in content
        or "Environment=CHECK_INTERVAL=" in content
    ):
        new_lines = []
        skipped_legacy_max_on = False
        for ln in content.splitlines(True):
            stripped = ln.strip()
            if stripped.startswith("Environment=MAX_ON_SECONDS="):
                # Removed from policy — do not write it back.
                skipped_legacy_max_on = True
                continue
            if stripped.startswith("Environment=NO_LINK_GRACE_SECONDS="):
                new_lines.append(
                    "Environment=NO_LINK_GRACE_SECONDS={}\n".format(
                        WIFI_TIMER_NO_LINK_GRACE_SECONDS
                    )
                )
            elif stripped.startswith("Environment=CHECK_INTERVAL="):
                new_lines.append(
                    "Environment=CHECK_INTERVAL={}\n".format(WIFI_TIMER_CHECK_INTERVAL)
                )
            else:
                new_lines.append(ln)
        content = "".join(new_lines)
        if "Environment=NO_LINK_GRACE_SECONDS=" not in content:
            content = content.replace("ExecStart=", env_block + "ExecStart=", 1)
        if skipped_legacy_max_on:
            print("Note: removed legacy MAX_ON_SECONDS from unit (no longer used).")
    else:
        content = content.replace(
            "ExecStart=",
            env_block + "ExecStart=",
            1,
        )

    with open(WIFI_TIMER_TARGET, "w") as f:
        f.write(content)
    print("Service unit written to {}".format(WIFI_TIMER_TARGET))
    print(
        "  NO_LINK_GRACE_SECONDS={} ({} min without wlan link → soft-sleep)".format(
            WIFI_TIMER_NO_LINK_GRACE_SECONDS,
            WIFI_TIMER_NO_LINK_GRACE_SECONDS // 60,
        )
    )

    print("Reloading systemd daemon...")
    run_cmd(["systemctl", "daemon-reload"], check=True)

    print("Enabling {} (start on boot)...".format(WIFI_TIMER_SERVICE_NAME))
    run_cmd(["systemctl", "enable", WIFI_TIMER_SERVICE_NAME], check=True)

    print("Starting {} ...".format(WIFI_TIMER_SERVICE_NAME))
    run_cmd(["systemctl", "restart", WIFI_TIMER_SERVICE_NAME], check=True)
    r = run_cmd(
        ["systemctl", "is-active", WIFI_TIMER_SERVICE_NAME], capture=True, timeout=5
    )
    status = r.stdout.strip() if r and r.stdout else "unknown"
    print("Service status: {}".format(status))

    print("\nPolicy:")
    print("  • While wlan is linked: WiFi stays ON (no time limit)")
    print(
        "  • After wlan is gone for {}s ({} min): soft-sleep until reboot".format(
            WIFI_TIMER_NO_LINK_GRACE_SECONDS,
            WIFI_TIMER_NO_LINK_GRACE_SECONDS // 60,
        )
    )
    print("  • Link returns during countdown: timer cancelled, stays ON")
    print("  • Soft sleep only (no rfkill block / no nmcli radio off)")
    print("\nUseful commands:")
    print("  sudo systemctl status {}".format(WIFI_TIMER_SERVICE_NAME))
    print("  sudo journalctl -u {} -f".format(WIFI_TIMER_SERVICE_NAME))
    return True


def _restore_wifi_radio():
    """
    Best-effort full WiFi restore after disabling the field timer.

    Clears leftover hard-off state from older timer versions
    (rfkill soft-block + NetworkManager WirelessEnabled=false) and brings
    wlan* interfaces back up so the OS/NM own the radio again.
    """
    print("Restoring WiFi radio to normal OS control...")
    run_cmd(["rfkill", "unblock", "wifi"], check=False)
    run_cmd(["rfkill", "unblock", "all"], check=False)
    run_cmd(["nmcli", "radio", "wifi", "on"], check=False)
    try:
        for name in os.listdir("/sys/class/net"):
            if name.startswith("wlan"):
                run_cmd(["ip", "link", "set", name, "up"], check=False)
    except OSError:
        pass
    print("  rfkill unblock + nmcli radio wifi on + wlan* up requested.")


def disable_wifi_field_timer():
    """Stop and disable the field WiFi timer; always restore WiFi control."""
    unit_present = os.path.isfile(WIFI_TIMER_TARGET)
    if not unit_present:
        print("Field WiFi timer unit is not installed ({}).".format(WIFI_TIMER_TARGET))
        print("Still restoring WiFi in case a previous run left the radio off.")
    else:
        print("Stopping and disabling {} ...".format(WIFI_TIMER_SERVICE_NAME))
        run_cmd(["systemctl", "stop", WIFI_TIMER_SERVICE_NAME], check=False)
        run_cmd(["systemctl", "disable", WIFI_TIMER_SERVICE_NAME], check=False)

        if ask_yes_no(
            "Remove unit file from /etc/systemd/system/ as well?",
            "y",
        ):
            try:
                os.remove(WIFI_TIMER_TARGET)
                print("Removed {}".format(WIFI_TIMER_TARGET))
                run_cmd(["systemctl", "daemon-reload"], check=False)
            except OSError as e:
                print("WARNING: could not remove unit file: {}".format(e))

    # Always restore — disable means "return WiFi to normal system control".
    # Older timer versions used persistent rfkill/nmcli radio off; clean those too.
    _restore_wifi_radio()

    print("Field WiFi timer disabled; WiFi restore requested.")


def manage_wifi_field_timer():
    """
    Menu entry: enable (install+start) or disable the field WiFi timer.

    Keep WiFi on while wlan is linked; soft-sleep only after no-link grace.
    See wifi_field_timer.sh.
    """
    print("=" * 60)
    print("  FIELD WiFi TIMER (power saving)")
    print("=" * 60)
    print("While wlan is linked: WiFi stays ON (home / remote SSH OK).")
    print(
        "After wlan is gone for {}s ({} min): soft-sleep until reboot (forest).".format(
            WIFI_TIMER_NO_LINK_GRACE_SECONDS,
            WIFI_TIMER_NO_LINK_GRACE_SECONDS // 60,
        )
    )
    print("Soft sleep = wlan down only (no persistent rfkill / nmcli radio off).")
    print("Disable always restores WiFi to normal OS control.")
    print()
    print("Current status:")
    for line in _wifi_timer_status_lines():
        print(line)
    print()

    print("  1) Enable / reinstall field WiFi timer (recommended for field units)")
    print("  2) Disable field WiFi timer")
    print("  3) Cancel")
    choice = {}
    config_parse(
        {
            "prompt": "Select an action",
            "type": int,
            "name": "wifi_timer_action",
            "valid": [1, 2, 3],
            "default": 1,
        },
        choice,
    )
    action = choice["wifi_timer_action"]
    if action == 1:
        enable_wifi_field_timer()
    elif action == 2:
        disable_wifi_field_timer()
    else:
        print("Cancelled.")


def show_status():
    """Print a summary of config.json, the systemd service, and GPIO overlay."""

    print("=" * 60)
    print("  CURRENT STATUS")
    print("=" * 60)

    # --- config.json ---
    print("\n--- config.json ---")
    config = load_config()
    if config is None:
        print("  NOT FOUND: {}".format(CONFIG_FILE))
    else:
        sensor_type = config.get("sensor", {}).get("sensor_type", "(unset)")
        upload_enabled = config.get("upload_enabled", "(unset)")
        test = config.get("test_mode", "(unset)")
        use_btn = config.get("sys", {}).get("use_system_shutdown_button", 0)
        print("  Path:               {}".format(CONFIG_FILE))
        print("  Sensor type:        {}".format(sensor_type))
        print("  upload_enabled:     {}".format(upload_enabled))
        print("  test_mode:          {}".format(test))
        print("  shutdown button:    {} (1 = system-wide dtoverlay)".format(use_btn))

    # --- systemd service ---
    print("\n--- systemd service ({}) ---".format(SERVICE_NAME))
    installed = os.path.isfile(SERVICE_TARGET)
    print("  Unit file installed: {}".format("yes" if installed else "no"))
    if installed:
        print("    Path: {}".format(SERVICE_TARGET))
        r = run_cmd(["systemctl", "is-enabled", SERVICE_NAME], capture=True, timeout=5)
        enabled = r.stdout.strip() if r and r.stdout else "unknown"
        print("  Enabled:             {}".format(enabled))
        r = run_cmd(["systemctl", "is-active", SERVICE_NAME], capture=True, timeout=5)
        active = r.stdout.strip() if r and r.stdout else "unknown"
        print("  Active:              {}".format(active))

    # --- Field WiFi timer ---
    print("\n--- field WiFi timer ({}) ---".format(WIFI_TIMER_SERVICE_NAME))
    for line in _wifi_timer_status_lines():
        print(line)

    # --- GPIO overlay ---
    print("\n--- GPIO shutdown overlay ---")
    boot_config = find_boot_config()
    if boot_config is None:
        print("  Boot config not found (/boot/config.txt or /boot/firmware/config.txt)")
    else:
        print("  Boot config: {}".format(boot_config))
        with open(boot_config, "r") as f:
            for ln in f:
                if ln.strip().startswith("dtoverlay=gpio-shutdown"):
                    print("  Overlay found: {}".format(ln.strip()))
                    break
            else:
                print("  No gpio-shutdown overlay found.")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main menu loop
# ---------------------------------------------------------------------------
def print_banner():
    print()
    print("=" * 60)
    print("  Eco Monitoring -- Installer & Configurator")
    print("  Repository: {}".format(REPO_DIR))
    print(
        "  Running as: {} (real user: {})".format(
            os.environ.get("USER", "?"), get_real_user()
        )
    )
    print("=" * 60)


def main():
    ensure_root()

    while True:
        print_banner()
        print()
        for key, label, _ in MENU_ITEMS:
            print("  {}) {}".format(key, label))
        print()

        choice_holder = {}
        config_parse(
            {
                "prompt": "Select an option",
                "type": int,
                "name": "menu_choice",
                "valid": [int(k) for k, _, _ in MENU_ITEMS],
            },
            choice_holder,
        )
        choice = str(choice_holder["menu_choice"])

        action = None
        for key, _, func_name in MENU_ITEMS:
            if key == choice:
                action = func_name
                break

        if action is None:
            print("Goodbye!")
            break

        print()
        globals()[action]()

        if action != "show_status":
            pause()


if __name__ == "__main__":
    main()
