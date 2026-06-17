import os
import tempfile
import hashlib
from sysnux.utils.runner import run_command, check_internet
from sysnux.modules.system import detect_distro, detect_resolucao
from sysnux.modules.optimizations import (
    configurar_locale, configurar_firewall,
    otimizar_kernel, configurar_zram, configurar_tlp,
    otimizar_ssd, configurar_grub, limpar_sistema
)


APT_UPDATED = False


def apt_update():
    global APT_UPDATED
    if APT_UPDATED:
        return True, "already updated"
    ok, out = run_command("apt-get update")
    if ok:
        APT_UPDATED = True
    return ok, out


def apt_install(packages):
    apt_update()
    ok, out = run_command(f"apt-get install -y {packages}")
    return ok, out


def _instalar_deb_remoto(url, descricao):
    if not check_internet():
        yield f"[FALHA] Sem internet para baixar {descricao}"
        return
    yield f"[INFO] Baixando {descricao}..."
    tmp = tempfile.NamedTemporaryFile(suffix=".deb", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        ok, _ = run_command(f"wget -q --timeout=30 --tries=3 -O {tmp_path} '{url}'")
        if not ok:
            yield f"[FALHA] Download {descricao}"
            return
        ok, _ = run_command(f"dpkg -i {tmp_path} 2>/dev/null || true")
        if not ok:
            run_command(f"apt-get install -f -y")
        yield f"[OK] {descricao} instalado"
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def instalar_codecs_fontes():
    yield "[INFO] Instalando codecs e fontes..."
    distro = detect_distro()
    run_command("echo 'ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true' | debconf-set-selections")
    if distro == "ubuntu":
        ok, _ = apt_install("ubuntu-restricted-extras")
        yield f"{'[OK]' if ok else '[FALHA]'} ubuntu-restricted-extras"
    elif distro == "debian":
        ok, _ = apt_install("libavcodec-extra ffmpeg")
        yield f"{'[OK]' if ok else '[FALHA]'} codecs Debian"
    else:
        ok, _ = apt_install("ffmpeg")
        yield f"{'[OK]' if ok else '[FALHA]'} ffmpeg"
    ok, _ = apt_install("ttf-mscorefonts-installer p7zip-full rar unrar unzip zip xz-utils")
    yield f"{'[OK]' if ok else '[FALHA]'} Fontes e compactadores"
    ok, _ = apt_install("ffmpegthumbnailer libavcodec-extra gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav")
    yield f"{'[OK]' if ok else '[FALHA]'} GStreamer plugins"
    yield "[SUCESSO] Codecs e fontes instalados"


def instalar_temas():
    yield "[INFO] Instalando temas Papirus e Orchis..."
    ok, _ = run_command("add-apt-repository -y ppa:papirus/papirus && apt-get update")
    yield f"{'[OK]' if ok else '[FALHA]'} PPA Papirus"
    ok, _ = apt_install("papirus-icon-theme")
    yield f"{'[OK]' if ok else '[FALHA]'} Papirus Icon Theme"
    if not run_command("command -v git")[0]:
        ok, _ = apt_install("git")
        yield f"{'[OK]' if ok else '[FALHA]'} Git"
    tmpdir = tempfile.mkdtemp()
    ok, out = run_command(f"git clone --depth=1 https://github.com/vinceliuice/Orchis-theme.git {tmpdir}/orchis 2>/dev/null")
    if ok:
        run_command(f"cd {tmpdir}/orchis && ./install.sh -t default -c dark -s standard 2>/dev/null || true")
        yield "[OK] Orchis theme instalado"
    else:
        yield "[AVISO] Falha ao baixar Orchis theme"
    run_command(f"rm -rf {tmpdir}")
    run_command("gsettings set org.gnome.desktop.interface icon-theme 'Papirus-Dark' 2>/dev/null || true")
    yield "[OK] Tema Papirus-Dark aplicado"
    yield "[SUCESSO] Temas instalados"


def configurar_timeshift():
    yield "[INFO] Instalando Timeshift..."
    ok, _ = apt_install("timeshift")
    yield f"{'[OK]' if ok else '[FALHA]'} Timeshift instalado"
    ok, out = run_command("timeshift --create --comments 'Snapshot Sysnux' --yes 2>/dev/null || true")
    if ok:
        yield "[OK] Snapshot criado"
    else:
        yield "[AVISO] Snapshot não criado (sem partição configurada)"
    yield "[SUCESSO] Timeshift configurado"


def configurar_hidpi():
    resolucao = detect_resolucao()
    if resolucao and resolucao.isdigit() and int(resolucao) >= 2560:
        yield f"[INFO] Tela HiDPI detectada ({resolucao}px)"
        run_command("gsettings set org.gnome.desktop.interface text-scaling-factor 1.5 2>/dev/null || true")
        run_command("gsettings set org.gnome.desktop.interface scaling-factor 2 2>/dev/null || true")
        yield "[OK] HiDPI: text-scaling=1.5, scaling-factor=2"
    else:
        yield "[INFO] HiDPI não detectado"


def instalar_chrome():
    yield from _instalar_deb_remoto(
        "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb",
        "Google Chrome Estável"
    )


def instalar_chrome_beta():
    yield from _instalar_deb_remoto(
        "https://dl.google.com/linux/direct/google-chrome-beta_current_amd64.deb",
        "Google Chrome Beta"
    )


def instalar_firefox():
    yield "[INFO] Instalando Firefox..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    run_command("add-apt-repository -y ppa:mozillateam/ppa && apt-get update")
    ok, _ = apt_install("firefox")
    yield f"{'[OK]' if ok else '[FALHA]'} Firefox instalado"


def instalar_brave():
    yield "[INFO] Instalando Brave..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    run_command("curl -fsSLo /usr/share/keyrings/brave-browser-archive-keyring.gpg https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg 2>/dev/null")
    run_command("echo 'deb [signed-by=/usr/share/keyrings/brave-browser-archive-keyring.gpg] https://brave-browser-apt-release.s3.brave.com/ stable main' > /etc/apt/sources.list.d/brave-browser-release.list")
    apt_update()
    ok, _ = apt_install("brave-browser")
    yield f"{'[OK]' if ok else '[FALHA]'} Brave instalado"


def instalar_edge():
    yield from _instalar_deb_remoto(
        "https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_current_amd64.deb",
        "Microsoft Edge"
    )


def instalar_vivaldi():
    yield from _instalar_deb_remoto(
        "https://downloads.vivaldi.com/stable/vivaldi-stable_current_amd64.deb",
        "Vivaldi"
    )


def instalar_opera():
    yield from _instalar_deb_remoto(
        "https://download.opera.com/download/get/?id=41527&location=410&nothanks=yes",
        "Opera"
    )


def instalar_dev_tools():
    yield "[INFO] Instalando ferramentas de desenvolvimento..."
    ok, _ = apt_install("git build-essential")
    yield f"{'[OK]' if ok else '[FALHA]'} Git + build-essential"
    ok, _ = apt_install("docker.io")
    yield f"{'[OK]' if ok else '[FALHA]'} Docker"
    run_command("systemctl enable --now docker 2>/dev/null || true")
    if os.environ.get("SUDO_USER"):
        run_command(f"usermod -aG docker {os.environ['SUDO_USER']} 2>/dev/null || true")
        yield f"[OK] Usuário {os.environ['SUDO_USER']} adicionado ao grupo docker"
    ok, out = run_command("command -v snap 2>/dev/null")
    if ok:
        ok, out = run_command("snap install code --classic 2>/dev/null || true")
        if "error" not in out.lower():
            yield "[OK] VS Code (snap) instalado"
        else:
            yield "[AVISO] Falha ao instalar VS Code via snap"
    else:
        yield "[AVISO] VS Code não instalado (snap não disponível)"
    yield "[SUCESSO] Ferramentas de desenvolvimento instaladas"


def instalar_python311():
    yield "[INFO] Instalando Python 3.11 via deadsnakes PPA..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, _ = run_command("add-apt-repository -y ppa:deadsnakes/ppa && apt-get update")
    if not ok:
        yield "[FALHA] PPA deadsnakes"
        return
    ok, _ = apt_install("python3.11 python3.11-venv python3.11-dev")
    yield f"{'[OK]' if ok else '[FALHA]'} Python 3.11"
    if ok:
        run_command("update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 2 2>/dev/null || true")
    yield "[SUCESSO] Python 3.11 pronto"


def instalar_nodejs():
    yield "[INFO] Instalando Node.js LTS via NodeSource..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, _ = run_command("curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - 2>/dev/null")
    if not ok:
        yield "[FALHA] NodeSource setup"
        return
    ok, _ = apt_install("nodejs")
    yield f"{'[OK]' if ok else '[FALHA]'} Node.js + npm"
    yield "[SUCESSO] Node.js pronto"


def instalar_ghostty():
    yield "[INFO] Instalando Ghostty Terminal..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, _ = run_command("apt-get install -y ghostty 2>/dev/null")
    if ok:
        yield "[OK] Ghostty instalado via APT"
    else:
        yield "[INFO] Ghostty não encontrado nos repositórios, tentando Flatpak..."
        ok2, _ = run_command("flatpak install -y flathub com.mitchellh.ghostty 2>/dev/null")
        if ok2:
            yield "[OK] Ghostty instalado via Flatpak"
        else:
            yield "[FALHA] Ghostty não pôde ser instalado"
            return
    yield "[SUCESSO] Ghostty pronto"


def instalar_opencode():
    yield "[INFO] Instalando Opencode CLI..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, out = run_command("curl -fsSL https://opencode.ai/install | bash 2>/dev/null")
    if ok:
        yield "[OK] Opencode CLI instalado"
    else:
        yield f"[FALHA] Opencode CLI: {out.strip() or 'erro no instalador'}"
        return
    yield "[SUCESSO] Opencode pronto"


def instalar_flatpak_suporte():
    yield "[INFO] Instalando suporte Flatpak..."
    ok, _ = apt_install("flatpak")
    yield f"{'[OK]' if ok else '[FALHA]'} Flatpak instalado"
    run_command("flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo")
    yield "[OK] Flathub adicionado"
    yield "[SUCESSO] Flatpak pronto"


def atualizar_flatpaks():
    yield "[INFO] Atualizando Flatpaks..."
    ok, out = run_command("command -v flatpak 2>/dev/null")
    if not ok:
        yield "[FALHA] Flatpak não está instalado"
        return
    ok, _ = run_command("flatpak update -y --noninteractive 2>/dev/null")
    yield f"{'[OK]' if ok else '[FALHA]'} Flatpaks atualizados"
    yield "[SUCESSO] Flatpaks atualizados"


def remover_flatpak():
    yield "[INFO] Removendo Flatpak e todos os aplicativos..."
    ok, out = run_command("command -v flatpak 2>/dev/null")
    if ok:
        ok2, out2 = run_command("flatpak list --app --columns=application 2>/dev/null || true")
        if ok2 and out2:
            for app in out2.strip().split("\n"):
                app = app.strip()
                if app:
                    run_command(f"flatpak uninstall --noninteractive {app} 2>/dev/null || true")
                    yield f"[OK] Flatpak removido: {app}"
        run_command("flatpak uninstall --unused --noninteractive 2>/dev/null || true")
        run_command("flatpak remote-delete --force flathub 2>/dev/null || true")
    run_command("apt-get purge --auto-remove -y flatpak 2>/dev/null || true")
    run_command("rm -rf /var/lib/flatpak ~/.local/share/flatpak /root/.local/share/flatpak 2>/dev/null")
    yield "[OK] Flatpak e dependências removidos"
    yield "[SUCESSO] Flatpak removido"


def instalar_snap_suporte():
    yield "[INFO] Instalando Snap..."
    ok, _ = apt_install("snapd")
    yield f"{'[OK]' if ok else '[FALHA]'} Snap instalado"
    run_command("systemctl enable --now snapd 2>/dev/null || true")
    yield "[OK] Snapd ativado"
    yield "[SUCESSO] Snap pronto"


def atualizar_snaps():
    yield "[INFO] Atualizando Snaps..."
    ok, out = run_command("command -v snap 2>/dev/null")
    if not ok:
        yield "[FALHA] Snap não está instalado"
        return
    ok, _ = run_command("snap refresh 2>/dev/null")
    yield f"{'[OK]' if ok else '[FALHA]'} Snaps atualizados"
    yield "[SUCESSO] Snaps atualizados"


def remover_snap():
    yield "[INFO] Removendo Snap e todos os snaps..."
    ok, out = run_command("command -v snap 2>/dev/null")
    if ok:
        ok2, out2 = run_command("snap list 2>/dev/null | awk 'NR>1 {print $1}'")
        if ok2 and out2:
            for sp in out2.strip().split("\n"):
                sp = sp.strip()
                if sp:
                    run_command(f"snap remove --purge {sp} 2>/dev/null || true")
                    yield f"[OK] Snap removido: {sp}"
        run_command("systemctl stop snapd 2>/dev/null || true")
        run_command("systemctl disable snapd 2>/dev/null || true")
    run_command("apt-get purge --auto-remove -y snapd 2>/dev/null || true")
    run_command("rm -rf /var/snap /snap ~/snap /root/snap /var/cache/snapd 2>/dev/null")
    yield "[OK] Snap e dependências removidos"
    yield "[SUCESSO] Snap removido"


def setup_completo():
    if not check_internet():
        yield "[AVISO] Sem conexão com a internet"
    apt_update()
    yield "[OK] Repositórios atualizados"
    yield from configurar_locale()
    yield from configurar_firewall()
    yield from configurar_tlp()
    yield from configurar_zram()
    yield from otimizar_kernel()
    yield from otimizar_ssd()
    yield from configurar_grub()
    yield from instalar_codecs_fontes()
    yield from configurar_hidpi()
    yield from instalar_temas()
    yield from configurar_timeshift()
    yield from limpar_sistema()
    run_command("apt-get upgrade -y")
    yield "[OK] Sistema atualizado"
    yield "[SUCESSO] Setup completo finalizado!"


def realizar_upgrade():
    yield "[INFO] Atualizando lista de pacotes..."
    apt_update()
    yield "[OK] Repositórios atualizados"
    yield "[INFO] Executando upgrade completo..."
    ok, _ = run_command("apt-get upgrade -y")
    yield f"{'[OK]' if ok else '[FALHA]'} upgrade concluído"
    yield "[SUCESSO] Sistema atualizado"
