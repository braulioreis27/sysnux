import os
import tempfile

from sysnux.utils.runner import run_command
from sysnux.modules.system import (
    get_cpu_info, get_memory_info, get_disk_info,
    detect_gpu, collect_system_info
)


def diagnostico_hardware():
    yield "=== CPU ==="
    info = get_cpu_info()
    yield f"  Modelo: {info.get('model', 'N/A')}"
    yield f"  Núcleos: {info.get('cores', 'N/A')}"
    yield ""
    yield "=== Memória ==="
    mem = get_memory_info()
    yield f"  Total: {mem.get('total', 'N/A')}"
    yield f"  Usado: {mem.get('used', 'N/A')}"
    yield f"  Disponível: {mem.get('available', 'N/A')}"
    yield ""
    yield "=== Discos ==="
    yield get_disk_info()
    yield ""
    yield "=== GPU ==="
    yield f"  {', '.join(detect_gpu())}"
    ok, out = run_command("nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used --format=csv,noheader 2>/dev/null")
    if ok and out:
        yield f"  NVIDIA: {out}"
    yield ""
    yield "=== Temperaturas ==="
    ok, out = run_command("sensors 2>/dev/null | grep -E 'Core|Package|temp|fan' | head -10")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield ""
    yield "=== Dispositivos de Áudio ==="
    ok, out = run_command("lspci 2>/dev/null | grep -i audio || true")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "  N/A"
    yield "[SUCESSO] Diagnóstico concluído"


def listar_dispositivos_usb_pci():
    yield "=== Dispositivos PCI ==="
    ok, out = run_command("lspci -nn 2>/dev/null | head -30")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "  lspci não disponível"
    yield ""
    yield "=== Dispositivos USB ==="
    ok, out = run_command("lsusb 2>/dev/null | head -20")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "  lsusb não disponível"
    yield ""
    yield "=== Módulos de Kernel Carregados ==="
    ok, out = run_command("lsmod 2>/dev/null | head -20")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "  lsmod não disponível"
    yield "[SUCESSO] Informações de hardware listadas"


def info_dmi_bios():
    yield "=== BIOS/UEFI ==="
    ok, out = run_command("dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release' | head -5")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "  dmidecode não instalado ou sem suporte"
    yield ""
    yield "=== Placa Mãe ==="
    ok, out = run_command("dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer|Product|Version' | head -3")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield ""
    yield "=== Chassis / Sistema ==="
    ok, out = run_command("dmidecode -t system 2>/dev/null | grep -E 'Manufacturer|Product|Version|Serial' | head -5")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield ""
    yield "=== Memória Física (slots) ==="
    ok, out = run_command("dmidecode -t memory 2>/dev/null | grep -E 'Size|Type|Speed|Manufacturer|Locator' | head -20")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield "[SUCESSO] Informações DMI/BIOS coletadas"


def teste_smart():
    yield "[INFO] Verificando saúde dos discos (SMART)..."
    ok, out = run_command("apt-get install -y smartmontools 2>/dev/null")
    ok, out = run_command("lsblk -d -o name 2>/dev/null | grep -vE 'loop|sr[0-9]|NAME'")
    if not ok or not out:
        yield "[FALHA] Não foi possível listar discos"
        return
    for disco in out.strip().split("\n"):
        disco = disco.strip()
        if not disco:
            continue
        yield f"--- SMART /dev/{disco} ---"
        ok2, out2 = run_command(f"smartctl -H /dev/{disco} 2>/dev/null | grep -E 'SMART overall-health|SMART Health Status|PASSED|FAILED'")
        if ok2 and out2:
            yield f"  {out2}"
        else:
            yield "  SMART não suportado"
        ok2, out2 = run_command(f"smartctl -A /dev/{disco} 2>/dev/null | grep -E 'Reallocated_Sector|Pending_Sector|Uncorrectable|Temperature_Celsius|Power_On_Hours'")
        if ok2 and out2:
            for line in out2.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 10:
                    yield f"  {parts[1]}: {parts[9]}"
    yield "[SUCESSO] Teste SMART concluído"


def teste_memoria():
    yield "[INFO] Testando RAM (100MB, 1 iteração)..."
    run_command("apt-get install -y memtester 2>/dev/null")
    ok, out = run_command("memtester 100M 1 2>/dev/null")
    if ok and out:
        for line in out.strip().split("\n")[-10:]:
            yield f"  {line}"
    else:
        yield "[FALHA] Teste de memória falhou"
    yield "[SUCESSO] Teste de RAM concluído"


def stress_cpu(duration=30):
    yield f"[AVISO] Teste de STRESS na CPU ({duration}s)..."
    run_command("apt-get install -y stress-ng 2>/dev/null")
    ok, out = run_command("nproc")
    cores = out.strip() if ok else "2"
    yield f"[INFO] Executando stress-ng com {cores} workers..."
    ok, out = run_command(f"stress-ng --cpu {cores} --cpu-method matrixprod --timeout {duration}s --metrics-brief 2>&1 | tail -5")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield "[SUCESSO] Stress test concluído"


def _detect_root_disk():
    ok, out = run_command("findmnt -n -o SOURCE / | sed 's/[0-9]*$//' | xargs basename 2>/dev/null")
    if ok and out:
        return out.strip()
    ok, out = run_command("lsblk -ndo PKNAME $(findmnt -n -o SOURCE / | sed 's/[0-9]*$//' | xargs basename) 2>/dev/null")
    if ok and out:
        return out.strip()
    return "sda"


def benchmark_disco(disco=None):
    if disco is None:
        disco = _detect_root_disk()
    yield f"[INFO] Benchmark do disco /dev/{disco}..."
    ok, out = run_command(f"hdparm -Tt /dev/{disco} 2>/dev/null")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "[AVISO] hdparm não disponível ou falhou"
    tmp = tempfile.NamedTemporaryFile(prefix="sysnux_bench_", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        ok, out = run_command(f"dd if=/dev/zero of={tmp_path} bs=1M count=512 conv=fdatasync 2>&1 | tail -1")
        if ok and out:
            yield f"  Escrita: {out}"
        ok, out = run_command(f"dd if={tmp_path} of=/dev/null bs=1M count=512 2>&1 | tail -1")
        if ok and out:
            yield f"  Leitura: {out}"
    finally:
        os.unlink(tmp_path)
    yield "[SUCESSO] Benchmark concluído"


def analise_boot():
    yield "=== Tempo de Boot ==="
    ok, out = run_command("systemd-analyze 2>/dev/null")
    yield f"  {out}" if ok else "  systemd-analyze não disponível"
    yield ""
    yield "=== Serviços Mais Lentos ==="
    ok, out = run_command("systemd-analyze blame 2>/dev/null | head -10")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield ""
    yield "=== Serviços Falhos ==="
    ok, out = run_command("systemctl --failed 2>/dev/null")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    else:
        yield "  Nenhum"
    yield "[SUCESSO] Análise de boot concluída"


def saude_bateria():
    yield "=== Informações da Bateria ==="
    ok, out = run_command("upower -e 2>/dev/null")
    if ok and out:
        bateria = ""
        for line in out.strip().split("\n"):
            if "battery" in line.lower():
                bateria = line.strip()
                break
        if bateria:
            ok2, out2 = run_command(f"upower -i {bateria} 2>/dev/null")
            if ok2 and out2:
                yield out2
            else:
                yield "  Falha ao obter informações da bateria"
        else:
            yield "  Nenhuma bateria detectada"
    else:
        ok, out = run_command("acpi -V 2>/dev/null")
        if ok and out:
            yield out
        else:
            yield "  Nenhuma informação de bateria disponível"
    yield "[SUCESSO] Bateria verificada"


def analise_rede():
    yield "=== Interfaces de Rede ==="
    ok, out = run_command("ip -br addr 2>/dev/null | grep -v lo")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield ""
    yield "=== Tabela de Roteamento ==="
    ok, out = run_command("ip route 2>/dev/null")
    if ok and out:
        yield f"  {out}"
    yield ""
    yield "=== DNS ==="
    ok, out = run_command("grep -E '^nameserver' /etc/resolv.conf 2>/dev/null")
    if ok and out:
        yield f"  {out}"
    yield ""
    yield "=== Portas em Escuta ==="
    ok, out = run_command("ss -tlnp 2>/dev/null | head -20")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield "[SUCESSO] Análise de rede concluída"


def varredura_rootkit():
    yield "=== Varredura de Rootkit ==="
    ok, out = run_command("command -v rkhunter 2>/dev/null")
    if ok:
        yield "[INFO] Usando rkhunter..."
        ok2, out2 = run_command("rkhunter --check --skip-keypress --report-warnings-only 2>/dev/null | tail -20")
        if ok2 and out2:
            for line in out2.strip().split("\n"):
                yield f"  {line}"
    else:
        ok, out = run_command("command -v chkrootkit 2>/dev/null")
        if ok:
            yield "[INFO] Usando chkrootkit..."
            ok2, out2 = run_command("chkrootkit -q 2>/dev/null | grep -v 'not infected' | head -20")
            if ok2 and out2:
                for line in out2.strip().split("\n"):
                    yield f"  {line}"
            else:
                yield "  Nenhuma infecção detectada"
        else:
            yield "[AVISO] Nenhuma ferramenta de rootkit instalada"
            yield "[INFO] Instale com: apt install rkhunter"
    yield ""
    yield "=== Processos Suspeitos (CPU/MEM > 50%) ==="
    ok, out = run_command("ps aux 2>/dev/null | awk '$3>50.0 || $4>50.0 {print \"  ALTA: \" $11 \" CPU:\" $3 \"% MEM:\" $4 \"%\"}' | head -5 || true")
    if ok and out:
        for line in out.strip().split("\n"):
            yield line
    else:
        yield "  Nenhum processo suspeito"
    yield ""
    yield "=== Portas Abertas Suspeitas ==="
    ok, out = run_command("ss -tlnp 2>/dev/null | grep -vE '127.0.0.1|::1|0.0.0.0' | head -10")
    if ok and out:
        for line in out.strip().split("\n"):
            yield f"  {line}"
    yield "[SUCESSO] Varredura concluída"


def gerar_relatorio():
    yield "[INFO] Gerando relatório completo..."
    info = collect_system_info()
    lines = [
        "============================================",
        " RELATÓRIO COMPLETO DO SISTEMA - Sysnux",
        "============================================",
        f" Hostname: {info['hostname']}",
        f" Sistema: {info['distro']}",
        f" Kernel: {info['kernel']}",
        f" Uptime: {info['uptime']}",
        f" IP: {info['ip']}",
        f" GPU: {', '.join(info['gpu'])}",
        f" Tipo: {info['tipo']}",
        "",
        "--- CPU ---",
        f"  Modelo: {info['cpu'].get('model', 'N/A')}",
        f"  Núcleos: {info['cpu'].get('cores', 'N/A')}",
        "",
        "--- Memória ---",
        f"  Total: {info['memory'].get('total', 'N/A')}",
        f"  Disponível: {info['memory'].get('available', 'N/A')}",
        "",
        "--- Discos ---",
    ]
    if info.get("disk"):
        lines.append(info["disk"])
    lines.append("")
    lines.append("[SUCESSO] Relatório gerado")
    for line in lines:
        yield line


def instalar_ferramentas_ti():
    yield "[INFO] Instalando todas as ferramentas de diagnóstico..."
    ok, _ = run_command("apt-get install -y inxi hwinfo lshw htop neofetch smartmontools memtester stress-ng dmidecode nmap net-tools dnsutils debsums deborphan testdisk sysstat iotop hdparm lm-sensors upower acpi rkhunter chkrootkit lynis usbutils pciutils nvme-cli")
    yield f"{'[OK]' if ok else '[FALHA]'} Ferramentas TI instaladas"
    yield "[SUCESSO] Todas as ferramentas instaladas"
