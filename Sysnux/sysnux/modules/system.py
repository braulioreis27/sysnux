import os
import re

from packaging.version import parse as parse_version
from sysnux.utils.runner import run_command, check_internet


def detect_distro():
    distro = "desconhecida"
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro_id = line.split("=", 1)[1].strip().strip('"')
                    ubuntu_like = {"ubuntu", "linuxmint", "pop", "elementary", "zorin"}
                    debian_like = {"debian", "raspbian"}
                    if distro_id in ubuntu_like:
                        distro = "ubuntu"
                    elif distro_id in debian_like:
                        distro = "debian"
                    else:
                        distro = distro_id
    except FileNotFoundError:
        pass
    return distro


def get_distro_pretty_name():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except FileNotFoundError:
        pass
    return "Linux"


def get_kernel():
    success, output = run_command("uname -r")
    return output if success else "desconhecido"


def get_kernel_version(ver):
    return re.sub(r'-(generic|amd64|cloud|aws|azure|gcp|kvm|lowlatency|oem|raspi|rt|sa|virtual).*', '', ver)


def detect_gpu():
    gpus = []
    success, output = run_command("lspci")
    if success:
        for line in output.lower().split("\n"):
            if "vga" in line or "3d" in line or "display" in line:
                if "nvidia" in line:
                    if "nvidia" not in gpus:
                        gpus.append("nvidia")
                if "amd" in line or "ati" in line:
                    if "amd" not in gpus:
                        gpus.append("amd")
                if "intel" in line:
                    if "intel" not in gpus:
                        gpus.append("intel")
    return gpus if gpus else ["desconhecida"]


def detect_tipo_sistema():
    if not os.path.isdir("/sys/class/power_supply"):
        return "desktop"
    try:
        supplies = os.listdir("/sys/class/power_supply")
        has_battery = any("BAT" in s for s in supplies)
        return "notebook" if has_battery else "desktop"
    except PermissionError:
        return "desktop"


def detect_resolucao():
    success, output = run_command("xrandr 2>/dev/null | grep '*' | awk '{print $1}' | head -1")
    if success and output:
        return output.split("x")[0]
    return None


def get_cpu_info():
    info = {}
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    info["model"] = line.split(":", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass
    success, output = run_command("nproc")
    if success and output:
        info["cores"] = output
    return info


def get_memory_info():
    success, output = run_command("free -h | grep Mem")
    if success and output:
        parts = output.split()
        return {"total": parts[1], "used": parts[2], "available": parts[6]}
    return {}


def get_disk_info():
    success, output = run_command("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE 2>/dev/null | grep -vE 'loop|sr[0-9]'")
    return output if success else ""


def get_uptime():
    success, output = run_command("uptime -p")
    return output if success else ""


def get_ip_address():
    success, output = run_command("ip -br addr 2>/dev/null | grep -v lo")
    return output if success else ""


def get_hostname():
    success, output = run_command("hostname")
    return output if success else ""


def verificar_update():
    """Checa GitHub releases por versão mais recente.
    Retorna (tem_update, latest_tag, download_url) ou (False, '', '').
    """
    if not check_internet():
        return (False, "", "")
    ok, out = run_command(
        "curl -sL --connect-timeout 5 --max-time 10 "
        "https://api.github.com/repos/braulioreis27/sysnux/releases/latest 2>/dev/null "
        "| python3 -c \"import json,sys; d=json.load(sys.stdin); "
        "print(d['tag_name']); print(d['html_url'])\" 2>/dev/null"
    )
    if not ok or not out:
        return (False, "", "")
    lines = out.strip().split("\n")
    if len(lines) < 2:
        return (False, "", "")
    latest = lines[0].strip()
    url = lines[1].strip()
    from sysnux import __version__
    try:
        current_ver = parse_version(__version__)
        latest_ver = parse_version(latest.lstrip("v"))
        has_update = latest_ver > current_ver
    except Exception:
        has_update = latest != __version__
    return (has_update, latest, url)


def collect_system_info():
    info = {
        "hostname": get_hostname(),
        "distro": get_distro_pretty_name(),
        "kernel": get_kernel(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "gpu": detect_gpu(),
        "uptime": get_uptime(),
        "ip": get_ip_address(),
        "tipo": detect_tipo_sistema(),
    }
    return info
