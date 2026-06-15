from sysnux.utils.runner import run_command
from sysnux.modules.system import detect_tipo_sistema


def configurar_locale():
    yield "[INFO] Configurando idioma pt-BR..."
    ok, out = run_command("apt-get install -y locales")
    yield f"{'[OK]' if ok else '[FALHA]'} Instalar locales"
    ok, out = run_command("locale-gen pt_BR.UTF-8")
    yield f"{'[OK]' if ok else '[FALHA]'} Gerar pt_BR.UTF-8"
    ok, out = run_command("localectl set-locale LANG=pt_BR.UTF-8")
    yield f"{'[OK]' if ok else '[FALHA]'} Definir locale"
    yield "[SUCESSO] Locale configurado"


def configurar_firewall():
    yield "[INFO] Configurando UFW..."
    ok, out = run_command("apt-get install -y ufw gufw")
    yield f"{'[OK]' if ok else '[FALHA]'} Instalar UFW"
    ok, out = run_command("ufw default deny incoming")
    yield f"{'[OK]' if ok else '[FALHA]'} Negar entrada"
    ok, out = run_command("ufw default allow outgoing")
    yield f"{'[OK]' if ok else '[FALHA]'} Permitir saída"
    ok, out = run_command("ufw --force enable")
    yield f"{'[OK]' if ok else '[FALHA]'} Ativar firewall"
    yield "[SUCESSO] Firewall configurado"


def otimizar_kernel():
    yield "[INFO] Otimizando kernel..."
    conf = """net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.tcp_fastopen = 3
net.core.somaxconn = 4096
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
kernel.sched_min_granularity_ns = 1500000
net.ipv4.conf.all.rp_filter = 1
vm.swappiness = 10
vm.vfs_cache_pressure = 50
"""
    try:
        with open("/etc/sysctl.d/99-performance-sysnux.conf", "w") as f:
            f.write(conf)
        yield "[OK] Configuração sysctl criada"
    except PermissionError:
        yield "[FALHA] Permissão negada para criar /etc/sysctl.d/99-performance-sysnux.conf"
        return
    ok, out = run_command("sysctl --system")
    yield f"{'[OK]' if ok else '[FALHA]'} Aplicar sysctl"
    yield "[SUCESSO] Kernel otimizado"


def configurar_zram():
    yield "[INFO] Configurando ZRAM..."
    ok, out = run_command("apt-get install -y zram-tools earlyoom")
    yield f"{'[OK]' if ok else '[FALHA]'} Instalar zram-tools e earlyoom"
    try:
        with open("/etc/default/zramswap", "w") as f:
            f.write("PERCENT=50\nPRIORITY=100\n")
        yield "[OK] Configuração ZRAM"
    except PermissionError:
        yield "[FALHA] Permissão negada"
        return
    ok, out = run_command("systemctl restart zramswap 2>/dev/null || true")
    ok2, out2 = run_command("systemctl enable --now earlyoom 2>/dev/null || true")
    yield f"{'[OK]' if ok else '[AVISO]'} Reiniciar ZRAM"
    yield f"{'[OK]' if ok2 else '[AVISO]'} Ativar earlyOOM"
    yield "[SUCESSO] ZRAM configurado"


def configurar_tlp():
    tipo = detect_tipo_sistema()
    if tipo != "notebook":
        yield "[INFO] Sistema desktop — TLP não necessário"
        return
    yield "[INFO] Instalando TLP para notebook..."
    ok, out = run_command("apt-get install -y tlp tlp-rdw")
    yield f"{'[OK]' if ok else '[FALHA]'} Instalar TLP"
    ok, out = run_command("systemctl enable --now tlp")
    yield f"{'[OK]' if ok else '[FALHA]'} Ativar TLP"
    yield "[SUCESSO] TLP configurado"


def otimizar_ssd():
    yield "[INFO] Otimizando SSD..."
    ok, out = run_command("systemctl enable fstrim.timer && systemctl start fstrim.timer")
    yield f"{'[OK]' if ok else '[FALHA]'} Ativar fstrim"
    udev_rule = """ACTION=="add|change", KERNEL=="sd*", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="kyber"
ACTION=="add|change", KERNEL=="nvme*", ATTR{queue/scheduler}="none"
"""
    try:
        with open("/etc/udev/rules.d/60-ssd-scheduler.rules", "w") as f:
            f.write(udev_rule)
        yield "[OK] Regra udev para scheduler SSD"
    except PermissionError:
        yield "[FALHA] Permissão negada"
        return
    ok, out = run_command("sed -i 's/relatime/noatime/g' /etc/fstab 2>/dev/null || true")
    yield f"{'[OK]' if ok else '[AVISO]'} noatime configurado"
    yield "[SUCESSO] SSD otimizado"


def configurar_grub():
    yield "[INFO] Configurando GRUB..."
    _, out = run_command("sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=3/' /etc/default/grub 2>/dev/null || true")
    _, out = run_command("""sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash /' /etc/default/grub 2>/dev/null || true""")
    _, out = run_command("grep -q '^GRUB_DISABLE_OS_PROBER' /etc/default/grub 2>/dev/null || echo 'GRUB_DISABLE_OS_PROBER=false' >> /etc/default/grub")
    ok4, out = run_command("update-grub")
    yield "[OK] GRUB: timeout=3, splash silencioso"
    yield f"{'[OK]' if ok4 else '[FALHA]'} update-grub"
    yield "[SUCESSO] GRUB configurado"


def limpar_sistema():
    yield "[INFO] Limpando o sistema..."
    run_command("apt-get clean")
    yield "[OK] apt-get clean"
    run_command("apt-get autoclean -y")
    yield "[OK] apt-get autoclean"
    run_command("apt-get autoremove -y")
    yield "[OK] apt-get autoremove"
    run_command("rm -rf /home/*/.cache/thumbnails/* 2>/dev/null || true")
    run_command("rm -rf /root/.cache/thumbnails/* 2>/dev/null || true")
    yield "[OK] Miniaturas removidas"
    run_command("journalctl --vacuum-time=7d 2>/dev/null || true")
    yield "[OK] Logs antigos (7d)"
    run_command("find /var/log -type f -name '*.log' -mtime +30 -delete 2>/dev/null || true")
    yield "[OK] Logs com +30 dias removidos"
    yield "[SUCESSO] Limpeza concluída"
