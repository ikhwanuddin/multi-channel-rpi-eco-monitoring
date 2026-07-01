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
  4. Full guided setup (1 -> 2 -> 3, recommended for new deployments)
  5. Migrate away from the legacy /etc/profile startup
  6. Show current status (config / service / GPIO overlay)

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
    ("7", "Show current status", "show_status"),
    ("8", "Exit", None),
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

    # offline_mode is always 1; online upload is handled at runtime by
    # internet-detection logic in record.py.
    offline_config = {"offline_mode": 1}

    deployment_info_options = [
        {
            "name": "has_internet",
            "type": int,
            "prompt": (
                "Deployment note: is internet sometimes available at this site?\n"
                "1 = Sometimes available (startup can enter upload mode when internet is reachable)\n"
                "0 = Typically no internet (startup will usually stay in recording mode)\n"
                "This value is informational and does not force runtime mode."
            ),
            "default": 1,
            "valid": [0, 1],
        },
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

    _configure_cloud_and_system(sensor_config, offline_config, deployment_config)


def _configure_cloud_and_system(sensor_config, offline_config, deployment_config):
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
        "offline_mode": offline_config["offline_mode"],
        "has_internet": deployment_config["has_internet"],
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

    marker = "# ── Eco-monitor shell shortcuts ──"
    # Also detect the old standalone monitor marker for backward compatibility
    old_marker = "monitor() {"
    with open(bashrc_path, "r") as f:
        content = f.read()

    if marker in content:
        print("Shell shortcuts are already present in {}.".format(bashrc_path))
        return

    snippet = """
# ── Eco-monitor shell shortcuts ──
# monitor   : tail live logs (Ctrl+C to quit)
# restarteco: daemon-reload + restart service
# statuseco : show service status
# stopeco   : stop service
# starteco  : start service
monitor() {
    echo "--- Menampilkan log real-time: eco-monitor.service (Ctrl+C untuk keluar) ---"
    sudo journalctl -u eco-monitor.service -f
}

alias restarteco='sudo systemctl daemon-reload && sudo systemctl restart eco-monitor.service'
alias statuseco='sudo systemctl status eco-monitor.service'
alias stopeco='sudo systemctl stop eco-monitor.service'
alias starteco='sudo systemctl start eco-monitor.service'
# ── end eco-monitor shortcuts ──
"""
    with open(bashrc_path, "a") as f:
        f.write("\n" + snippet.strip() + "\n")

    fix_ownership(bashrc_path)

    print("Successfully added shell shortcuts to {}".format(bashrc_path))
    print("Shortcuts installed: monitor, restarteco, statuseco, stopeco, starteco")
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

    print("\n--- Step 1 of 4: Configure sensor & generate config.json ---")
    configure_sensor_and_config()

    print("\n--- Step 2 of 4: Install systemd service ---")
    install_service()

    print("\n--- Step 3 of 4: Configure GPIO shutdown button ---")
    if ask_yes_no("Configure the GPIO shutdown button now?", "y"):
        configure_gpio()
    else:
        print("Skipping GPIO configuration. You can do it later via menu option 3.")

    print("\n--- Step 4 of 4: Install shell shortcuts ---")
    if ask_yes_no(
        "Install shell shortcuts (monitor, restarteco, ...) to .bashrc?", "y"
    ):
        install_shell_monitor_alias()
    else:
        print("Skipping shell shortcuts installation.")

    print("\n" + "=" * 60)
    print("  Full setup complete!")
    print("=" * 60)
    print("Next steps:")
    print("  1. Reboot to apply the GPIO overlay (if configured):")
    print("       sudo reboot")
    print("  2. After reboot, check the service:")
    print("       sudo systemctl status {}".format(SERVICE_NAME))
    print("     Or simply type `monitor` if you installed the shortcut.")


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
# Menu action 6: show current status
# ---------------------------------------------------------------------------
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
        offline = config.get("offline_mode", "(unset)")
        test = config.get("test_mode", "(unset)")
        use_btn = config.get("sys", {}).get("use_system_shutdown_button", 0)
        print("  Path:               {}".format(CONFIG_FILE))
        print("  Sensor type:        {}".format(sensor_type))
        print("  offline_mode:       {}".format(offline))
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
