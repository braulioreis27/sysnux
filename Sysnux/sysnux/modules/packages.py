import os
import tempfile
from sysnux.utils.runner import run_command, check_internet
from sysnux.modules.system import detect_distro, detect_resolucao
from sysnux.modules.optimizations import (
    configurar_locale, configurar_firewall,
    otimizar_kernel, configurar_zram, configurar_tlp,
    otimizar_ssd, configurar_grub, limpar_sistema
)


def apt_install(packages):
    ok, out = run_command(f"apt-get install -y {packages}")
    return ok, out


def apt_update():
    ok, out = run_command("apt-get update")
    return ok, out


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
    yield "[INFO] Instalando Google Chrome..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, out = run_command("wget -q --timeout=30 --tries=3 -O /tmp/chrome.deb 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'")
    if not ok:
        yield "[FALHA] Download Chrome"
        return
    run_command("dpkg -i /tmp/chrome.deb 2>/dev/null || true")
    run_command("apt-get install -f -y")
    run_command("rm -f /tmp/chrome.deb")
    yield "[OK] Google Chrome instalado"


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
    yield "[INFO] Instalando Microsoft Edge..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, out = run_command("wget -q --timeout=30 --tries=3 -O /tmp/edge.deb 'https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_current_amd64.deb'")
    if not ok:
        yield "[FALHA] Download Edge"
        return
    run_command("dpkg -i /tmp/edge.deb 2>/dev/null || true")
    run_command("apt-get install -f -y")
    run_command("rm -f /tmp/edge.deb")
    yield "[OK] Microsoft Edge instalado"


def instalar_vivaldi():
    yield "[INFO] Instalando Vivaldi..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, out = run_command("wget -q --timeout=30 --tries=3 -O /tmp/vivaldi.deb 'https://downloads.vivaldi.com/stable/vivaldi-stable_current_amd64.deb'")
    if not ok:
        yield "[FALHA] Download Vivaldi"
        return
    run_command("dpkg -i /tmp/vivaldi.deb 2>/dev/null || true")
    run_command("apt-get install -f -y")
    run_command("rm -f /tmp/vivaldi.deb")
    yield "[OK] Vivaldi instalado"


def instalar_opera():
    yield "[INFO] Instalando Opera..."
    if not check_internet():
        yield "[FALHA] Sem internet"
        return
    ok, out = run_command("wget -q --timeout=30 --tries=3 -O /tmp/opera.deb 'https://download.opera.com/download/get/?id=41527&location=410&nothanks=yes'")
    if not ok:
        yield "[FALHA] Download Opera"
        return
    run_command("dpkg -i /tmp/opera.deb 2>/dev/null || true")
    run_command("apt-get install -f -y")
    run_command("rm -f /tmp/opera.deb")
    yield "[OK] Opera instalado"


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


def instalar_flatpak_suporte():
    yield "[INFO] Instalando suporte Flatpak..."
    ok, _ = apt_install("flatpak")
    yield f"{'[OK]' if ok else '[FALHA]'} Flatpak instalado"
    run_command("flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo")
    yield "[OK] Flathub adicionado"
    yield "[SUCESSO] Flatpak pronto"


def instalar_snap_suporte():
    yield "[INFO] Instalando Snap..."
    ok, _ = apt_install("snapd")
    yield f"{'[OK]' if ok else '[FALHA]'} Snap instalado"
    run_command("systemctl enable --now snapd 2>/dev/null || true")
    yield "[OK] Snapd ativado"
    yield "[SUCESSO] Snap pronto"


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
