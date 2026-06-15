#!/usr/bin/env bash

################################################################################
# Script Pós-Formatação - Ubuntu/Linux Mint v7.0
#------------------------------------------------------------------------------#
# Versão: 7.0.0
# Descrição: Ferramenta profissional para configuração e manutenção
#            de sistemas Ubuntu/Linux Mint e derivados Debian.
# Licença: MIT
################################################################################

set -o pipefail
IFS=$'\n\t'
shopt -s nullglob

readonly SCRIPT_VERSAO="7.0.0"
readonly SCRIPT_NOME="$(basename "$0")"
readonly ARQUIVO_LOG="/var/log/setup-pro-$(date +%Y%m%d_%H%M%S).log"
readonly DIR_BACKUP="/var/backups/setup-pro"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)

readonly COR_INFO='\033[0;36m'
readonly COR_AVISO='\033[0;33m'
readonly COR_ERRO='\033[0;31m'
readonly COR_SUCESSO='\033[0;32m'
readonly COR_DESTAQUE='\033[1;35m'
readonly COR_MENU='\033[1;34m'
readonly COR_HEADER='\033[1;37;44m'
readonly COR_RESET='\033[0m'
readonly BOLD='\033[1m'

MODO_STRICT=false
MODO_VERBOSE=false
MODO_PROFISSIONAL=false

APT_UPDATED=false

# ----------------------------------------------------------------------
# Limpeza na saída (trap)
# ----------------------------------------------------------------------

_cleanup() {
    local exit_code=$?
    echo ""
    echo -e "${COR_AVISO}[!] Script interrompido pelo usuário.${COR_RESET}"
    exit "$exit_code"
}

trap _cleanup SIGINT SIGTERM

# ----------------------------------------------------------------------
# Utilitárias
# ----------------------------------------------------------------------

log_mensagem() {
    local tipo="$1" mensagem="$2" cor=""
    local timestamp
    timestamp=$(date '+%H:%M:%S')
    case "$tipo" in
        INFO)    cor="$COR_INFO" ;;
        AVISO)   cor="$COR_AVISO" ;;
        ERRO)    cor="$COR_ERRO" ;;
        SUCESSO) cor="$COR_SUCESSO" ;;
        DEBUG)   [[ "$MODO_VERBOSE" == true ]] && cor="$COR_INFO" || return ;;
        *)       cor="$COR_RESET" ;;
    esac
    echo -e "${cor}[${timestamp}] [${tipo}] ${mensagem}${COR_RESET}" | tee -a "$ARQUIVO_LOG"
}

verificar_root() {
    if [[ "$EUID" -ne 0 ]]; then
        echo -e "${COR_ERRO}[ERRO] Execute como root (sudo $SCRIPT_NOME).${COR_RESET}"
        exit 1
    fi
}

executar_comando_seguro() {
    local descricao="$1"
    shift
    log_mensagem "INFO" "${descricao}..."
    if "$@" >> "$ARQUIVO_LOG" 2>&1; then
        log_mensagem "SUCESSO" "${descricao} — OK"
        return 0
    else
        local codigo_erro=$?
        log_mensagem "ERRO" "FALHA (código ${codigo_erro}): ${descricao}"
        [[ "$MODO_STRICT" == true ]] && exit "$codigo_erro"
        return 1
    fi
}

confirmar_acao() {
    local mensagem="$1"
    local resposta=""
    echo -e "${COR_AVISO}${mensagem} (s/N)${COR_RESET}"
    read -r resposta
    [[ "$resposta" =~ ^[Ss]$ ]] && return 0 || return 1
}

pausa() {
    echo ""
    read -rp "Pressione Enter para continuar..." dummy
}

apt_update_seguro() {
    [[ "$APT_UPDATED" == true ]] && return 0
    if executar_comando_seguro "Atualizar lista de pacotes" apt-get update; then
        APT_UPDATED=true
    fi
}

apt_instalar() {
    apt_update_seguro || return 1
    executar_comando_seguro "Instalar pacotes: $*" apt-get install -y "$@"
}

verificar_internet() {
    if ! ping -c 1 -W 2 8.8.8.8 &>/dev/null && \
       ! ping -c 1 -W 2 1.1.1.1 &>/dev/null; then
        log_mensagem "AVISO" "Sem conexão com a internet. Verifique a rede."
        if ! confirmar_acao "Continuar mesmo assim?"; then
            log_mensagem "INFO" "Operação cancelada pelo usuário."
            return 1
        fi
    fi
    return 0
}

baixar_arquivo() {
    local url="$1" destino="$2" descricao="$3"
    log_mensagem "INFO" "Baixando ${descricao}..."
    if wget -q --timeout=30 --tries=3 -O "$destino" "$url" 2>/dev/null; then
        log_mensagem "SUCESSO" "Download concluído: ${descricao}"
        return 0
    else
        log_mensagem "ERRO" "Falha no download: ${descricao}"
        return 1
    fi
}

instalar_deb_remoto() {
    local url="$1" destino="$2" descricao="$3"
    if baixar_arquivo "$url" "$destino" "$descricao"; then
        executar_comando_seguro "Instalar ${descricao}" dpkg -i "$destino"
        executar_comando_seguro "Corrigir dependências" apt-get install -f -y
        rm -f "$destino"
    fi
}

sudo_user() {
    if [[ -n "${SUDO_USER:-}" ]]; then
        sudo -u "$SUDO_USER" "$@"
    else
        "$@"
    fi
}

# ----------------------------------------------------------------------
# Detecção de Hardware
# ----------------------------------------------------------------------

detectar_gpu() {
    local gpus=()
    lspci 2>/dev/null | grep -qiE 'vga.*nvidia|3d.*nvidia' && gpus+=("nvidia")
    lspci 2>/dev/null | grep -qiE 'vga.*amd|vga.*ati|3d.*amd' && gpus+=("amd")
    lspci 2>/dev/null | grep -qiE 'vga.*intel' && gpus+=("intel")
    [[ ${#gpus[@]} -eq 0 ]] && echo "desconhecida" || echo "${gpus[@]}"
}

detectar_tipo_sistema() {
    if [[ -d "/sys/class/power_supply" ]] && \
       [[ "$(ls -A /sys/class/power_supply/ 2>/dev/null | grep -vc '^$')" -gt 0 ]] && \
       ! ls /sys/class/power_supply/ 2>/dev/null | grep -q "AC"; then
        echo "notebook"
    else
        echo "desktop"
    fi
}

detectar_resolucao() {
    if command -v xrandr &>/dev/null; then
        xrandr 2>/dev/null | grep '*' | awk '{print $1}' | head -1 | cut -d'x' -f1
    elif command -v xdpyinfo &>/dev/null; then
        xdpyinfo 2>/dev/null | grep dimensions | awk '{print $2}' | cut -d'x' -f1
    fi
}

get_kernel_version() {
    local ver="$1"
    echo "$ver" | sed -E 's/-(generic|amd64|cloud|aws|azure|gcp|kvm|lowlatency|oem|raspi|rt|sa|virtual).*//'
}

detectar_distro() {
    local id like=""
    if [[ -f /etc/os-release ]]; then
        id=$(grep -E '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"')
        like=$(grep -E '^ID_LIKE=' /etc/os-release | cut -d= -f2 | tr -d '"')
    fi
    case "$id" in
        ubuntu|linuxmint|pop|elementary|zorin) echo "ubuntu" ;;
        debian|raspbian) echo "debian" ;;
        *) [[ "$like" == *"debian"* ]] && echo "debian" || echo "desconhecida" ;;
    esac
}

# ----------------------------------------------------------------------
# Módulos de Configuração
# ----------------------------------------------------------------------

configurar_locale() {
    log_mensagem "INFO" "=== Configurando idioma pt-BR ==="
    apt_instalar locales
    executar_comando_seguro "Gerar pt_BR.UTF-8" locale-gen pt_BR.UTF-8
    executar_comando_seguro "Definir locale" localectl set-locale LANG=pt_BR.UTF-8
}

configurar_firewall() {
    log_mensagem "INFO" "=== Configurando Firewall ==="
    if confirmar_acao "Instalar e configurar UFW (firewall)?"; then
        apt_instalar ufw gufw
        executar_comando_seguro "Negar entrada" ufw default deny incoming
        executar_comando_seguro "Permitir saída" ufw default allow outgoing
        executar_comando_seguro "Ativar firewall" ufw --force enable
    else
        log_mensagem "INFO" "Firewall ignorado pelo usuário."
    fi
}

instalar_codecs_fontes() {
    log_mensagem "INFO" "=== Codecs e Fontes ==="
    if confirmar_acao "Instalar codecs restritos e fontes Microsoft?"; then
        echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

        local distro
        distro=$(detectar_distro)
        case "$distro" in
            ubuntu)
                apt_instalar ubuntu-restricted-extras
                ;;
            debian)
                apt_instalar libavcodec-extra ffmpeg
                ;;
            *)
                log_mensagem "AVISO" "Distro não reconhecida. Instalando pacotes genéricos."
                apt_instalar ffmpeg
                ;;
        esac
        apt_instalar ttf-mscorefonts-installer
        apt_instalar p7zip-full rar unrar unzip zip xz-utils
        apt_instalar ffmpegthumbnailer libavcodec-extra gstreamer1.0-plugins-{good,bad,ugly} gstreamer1.0-libav
        log_mensagem "SUCESSO" "Codecs e fontes instalados."
    fi
}

otimizar_kernel() {
    log_mensagem "INFO" "=== Otimizando Kernel ==="
    if confirmar_acao "Aplicar otimizações de kernel (BBR, swappiness, buffers)?"; then
        local arquivo_conf="/etc/sysctl.d/99-performance-pro.conf"
        cat > "$arquivo_conf" <<'EOF'
net.core.default_qdisc = fq
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
EOF
        executar_comando_seguro "Aplicar sysctl" sysctl --system
    fi
}

configurar_zram() {
    log_mensagem "INFO" "=== ZRAM e earlyOOM ==="
    if confirmar_acao "Configurar ZRAM (swap comprimida) e earlyOOM?"; then
        apt_instalar zram-tools earlyoom
        cat > /etc/default/zramswap <<'EOF'
PERCENT=50
PRIORITY=100
EOF
        executar_comando_seguro "Reiniciar ZRAM" systemctl restart zramswap 2>/dev/null || true
        executar_comando_seguro "Ativar earlyOOM" systemctl enable --now earlyoom
    fi
}

configurar_tlp_notebook() {
    if [[ "$(detectar_tipo_sistema)" == "notebook" ]]; then
        log_mensagem "INFO" "=== TLP para Notebook ==="
        if confirmar_acao "Instalar TLP para otimização de bateria?"; then
            apt_instalar tlp tlp-rdw
            executar_comando_seguro "Ativar TLP" systemctl enable --now tlp
        fi
    fi
}

configurar_hidpi() {
    local resolucao
    resolucao=$(detectar_resolucao)
    if [[ -n "$resolucao" ]] && [[ "$resolucao" -ge 2560 ]]; then
        log_mensagem "INFO" "=== Tela HiDPI detectada (${resolucao}px) ==="
        echo "Fatores: 1=125%  2=150%  3=175%  4=200%  0=Pular"
        local escolha_hidpi=""
        read -rp "Escolha [0-4]: " escolha_hidpi
        local fator=""
        local escala_inteira=""
        case "$escolha_hidpi" in
            1) fator=1.25; escala_inteira=2 ;;
            2) fator=1.5;  escala_inteira=2 ;;
            3) fator=1.75; escala_inteira=2 ;;
            4) fator=2.0;  escala_inteira=2 ;;
            0|*) return ;;
        esac
        if command -v gsettings &>/dev/null; then
            sudo_user gsettings set org.gnome.desktop.interface text-scaling-factor "$fator" 2>/dev/null || true
            sudo_user gsettings set org.gnome.desktop.interface scaling-factor "$escala_inteira" 2>/dev/null || true
        fi
        log_mensagem "SUCESSO" "HiDPI: text-scaling=${fator}, scaling-factor=${escala_inteira}"
    fi
}

instalar_temas() {
    log_mensagem "INFO" "=== Temas e Ícones ==="
    if confirmar_acao "Instalar temas Papirus e Orchis?"; then
        if command -v add-apt-repository &>/dev/null; then
            executar_comando_seguro "Adicionar PPA Papirus" add-apt-repository -y ppa:papirus/papirus
            apt_update_seguro
            apt_instalar papirus-icon-theme
        else
            apt_instalar software-properties-common
            executar_comando_seguro "Adicionar PPA Papirus" add-apt-repository -y ppa:papirus/papirus
            apt_update_seguro
            apt_instalar papirus-icon-theme
        fi
        if ! command -v git &>/dev/null; then
            apt_instalar git
        fi
        local tmp_dir
        tmp_dir=$(mktemp -d)
        if git clone --depth=1 https://github.com/vinceliuice/Orchis-theme.git "$tmp_dir/orchis" 2>/dev/null; then
            if [[ -f "$tmp_dir/orchis/install.sh" ]]; then
                (cd "$tmp_dir/orchis" && ./install.sh -t default -c dark -s standard) 2>/dev/null || true
            fi
            rm -rf "$tmp_dir/orchis"
        fi
        rm -rf "$tmp_dir"

        if command -v gsettings &>/dev/null; then
            sudo_user gsettings set org.gnome.desktop.interface icon-theme 'Papirus-Dark' 2>/dev/null || true
        fi
    fi
}

configurar_timeshift() {
    log_mensagem "INFO" "=== Timeshift ==="
    if confirmar_acao "Instalar e criar snapshot com Timeshift?"; then
        apt_instalar timeshift
        executar_comando_seguro "Criar snapshot" timeshift --create --comments "Snapshot v${SCRIPT_VERSAO}" --yes 2>/dev/null || \
            log_mensagem "AVISO" "Snapshot não criado (sem partição configurada)."
    fi
}

otimizar_ssd() {
    log_mensagem "INFO" "=== Otimização SSD ==="
    if confirmar_acao "Aplicar otimizações para SSD (fstrim, scheduler, noatime)?"; then
        executar_comando_seguro "Ativar fstrim timer" systemctl enable fstrim.timer
        executar_comando_seguro "Iniciar fstrim timer" systemctl start fstrim.timer

        local arquivo_conf="/etc/udev/rules.d/60-ssd-scheduler.rules"
        cat > "$arquivo_conf" <<'EOF'
# SSD: usar scheduler kyber ou none (nvme)
ACTION=="add|change", KERNEL=="sd*", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="kyber"
ACTION=="add|change", KERNEL=="nvme*", ATTR{queue/scheduler}="none"
EOF
        log_mensagem "INFO" "Regra udev para scheduler SSD criada."

        # Aplicar noatime para partições montadas
        local fstab_backup="/etc/fstab.bak.${TIMESTAMP}"
        cp /etc/fstab "$fstab_backup" 2>/dev/null || true
        sed -i 's/relatime/noatime/g' /etc/fstab 2>/dev/null || true
        log_mensagem "SUCESSO" "Otimizações SSD aplicadas (fstrim ativado, noatime configurado)."
        log_mensagem "AVISO" "Backup do fstab salvo em $fstab_backup"
    fi
}

configurar_grub() {
    log_mensagem "INFO" "=== Configuração GRUB ==="
    if confirmar_acao "Otimizar GRUB (reduzir timeout, desabilitar memtest, modo silencioso)?"; then
        local grub_conf="/etc/default/grub"
        local grub_backup="/etc/default/grub.bak.${TIMESTAMP}"
        cp "$grub_conf" "$grub_backup" 2>/dev/null || true

        sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=3/' "$grub_conf" 2>/dev/null
        sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="quiet splash /' "$grub_conf" 2>/dev/null
        grep -q '^GRUB_DISABLE_OS_PROBER' "$grub_conf" 2>/dev/null || \
            echo 'GRUB_DISABLE_OS_PROBER=false' >> "$grub_conf"

        executar_comando_seguro "Atualizar GRUB" update-grub
        log_mensagem "SUCESSO" "GRUB configurado (timeout=3, inicialização silenciosa)."
        log_mensagem "AVISO" "Backup em $grub_backup"
    fi
}

limpar_sistema() {
    log_mensagem "INFO" "=== Limpeza Geral do Sistema ==="
    if confirmar_acao "Limpar cache de pacotes, miniaturas, lixeiras e temporários?"; then
        apt-get clean 2>/dev/null
        apt-get autoclean -y 2>/dev/null
        apt-get autoremove -y 2>/dev/null
        rm -rf /home/*/.cache/thumbnails/* 2>/dev/null || true
        rm -rf /root/.cache/thumbnails/* 2>/dev/null || true
        journalctl --vacuum-time=7d 2>/dev/null || true
        find /var/log -type f -name "*.log" -mtime +30 -delete 2>/dev/null || true
        rm -rf /tmp/* 2>/dev/null || true
        log_mensagem "SUCESSO" "Limpeza geral concluída."
    fi
}

# ----------------------------------------------------------------------
# Drivers GPU
# ----------------------------------------------------------------------

menu_drivers_gpu() {
    local op_driver=""
    local gpus_detectadas=()
    mapfile -t gpus_detectadas < <(detectar_gpu)

    clear
    echo -e "${COR_HEADER}========================================${COR_RESET}"
    echo -e "${COR_HEADER}  CONFIGURAÇÃO DE DRIVERS DE VÍDEO${COR_RESET}"
    echo -e "${COR_HEADER}========================================${COR_RESET}"
    echo ""

    if [[ "${gpus_detectadas[0]}" == "desconhecida" ]]; then
        echo -e "${COR_AVISO}Nenhuma GPU dedicada detectada. Usando drivers do kernel.${COR_RESET}"
        pausa
        return
    fi

    echo -e "GPUs detectadas: ${COR_SUCESSO}${gpus_detectadas[*]}${COR_RESET}"

    # NVIDIA Optimus
    if [[ ${#gpus_detectadas[@]} -ge 2 ]] && \
       [[ " ${gpus_detectadas[*]} " =~ " nvidia " ]] && \
       [[ " ${gpus_detectadas[*]} " =~ " intel " ]]; then
        echo -e "\n${COR_DESTAQUE}NVIDIA Optimus detectado!${COR_RESET}"
        echo "1. NVIDIA Prime (Recomendado)"
        echo "2. Apenas Intel"
        echo "3. Apenas NVIDIA"
        echo "0. Pular"
        read -rp "Escolha [0-3]: " op_driver
        case "$op_driver" in
            1)
                apt_instalar nvidia-driver-535 nvidia-prime
                prime-select on-demand 2>/dev/null || true
                ;;
            2) prime-select intel 2>/dev/null || true ;;
            3)
                apt_instalar nvidia-driver-535
                prime-select nvidia 2>/dev/null || true
                ;;
        esac
        pausa
        return
    fi

    for gpu in "${gpus_detectadas[@]}"; do
        echo -e "\n${COR_MENU}--- GPU ${gpu^^} ---${COR_RESET}"
        case "$gpu" in
            nvidia)
                echo "1. NVIDIA 535 (Estável)"
                echo "2. NVIDIA 545 (Recente)"
                echo "3. NVIDIA + CUDA"
                echo "0. Pular"
                read -rp "Escolha [0-3]: " op_driver
                case "$op_driver" in
                    1) apt_instalar nvidia-driver-535 ;;
                    2) apt_instalar nvidia-driver-545 ;;
                    3) apt_instalar nvidia-driver-535 nvidia-cuda-toolkit ;;
                esac
                ;;
            amd)
                echo "1. Mesa Vulkan (Recomendado)"
                echo "0. Pular"
                read -rp "Escolha [0-1]: " op_driver
                case "$op_driver" in
                    1) apt_instalar mesa-vulkan-drivers vulkan-tools mesa-utils ;;
                esac
                ;;
            intel)
                echo "1. Intel Media Driver"
                echo "0. Pular"
                read -rp "Escolha [0-1]: " op_driver
                case "$op_driver" in
                    1) apt_instalar intel-media-va-driver ;;
                esac
                ;;
        esac
    done
    pausa
}

# ----------------------------------------------------------------------
# Navegadores
# ----------------------------------------------------------------------

menu_navegadores() {
    local escolhas_naveg=""

    clear
    echo -e "${COR_HEADER}========================================${COR_RESET}"
    echo -e "${COR_HEADER}  INSTALAÇÃO DE NAVEGADORES${COR_RESET}"
    echo -e "${COR_HEADER}========================================${COR_RESET}"
    echo ""
    echo "Digite os números separados por espaço (ex: 1 4 5)"
    echo "1. Google Chrome Estável"
    echo "2. Google Chrome Beta"
    echo "3. Mozilla Firefox (PPA oficial)"
    echo "4. Brave Browser"
    echo "5. Microsoft Edge"
    echo "6. Vivaldi"
    echo "7. Opera"
    echo "8. TODOS"
    echo "0. Nenhum"
    echo ""
    read -rp "Opções: " escolhas_naveg

    [[ -z "$escolhas_naveg" ]] && return

    for op_nav in $escolhas_naveg; do
        case "$op_nav" in
            1) instalar_chrome_estavel ;;
            2) instalar_chrome_beta ;;
            3) instalar_firefox_ppa ;;
            4) instalar_brave ;;
            5) instalar_edge ;;
            6) instalar_vivaldi ;;
            7) instalar_opera ;;
            8)
                instalar_chrome_estavel
                instalar_firefox_ppa
                instalar_brave
                instalar_edge
                instalar_vivaldi
                instalar_opera
                break
                ;;
            0) pausa; return ;;
        esac
    done
    pausa
}

instalar_chrome_estavel() {
    verificar_internet || return 1
    local url="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    instalar_deb_remoto "$url" "/tmp/chrome.deb" "Google Chrome Estável"
}

instalar_chrome_beta() {
    verificar_internet || return 1
    local url="https://dl.google.com/linux/direct/google-chrome-beta_current_amd64.deb"
    instalar_deb_remoto "$url" "/tmp/chrome-beta.deb" "Google Chrome Beta"
}

instalar_firefox_ppa() {
    verificar_internet || return 1
    executar_comando_seguro "Adicionar PPA Firefox" add-apt-repository -y ppa:mozillateam/ppa
    apt_update_seguro
    apt_instalar firefox
}

instalar_brave() {
    verificar_internet || return 1
    apt_instalar curl
    local keyring="/usr/share/keyrings/brave-browser-archive-keyring.gpg"
    curl -fsSLo "$keyring" https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg
    echo "deb [signed-by=${keyring}] https://brave-browser-apt-release.s3.brave.com/ stable main" | \
        tee /etc/apt/sources.list.d/brave-browser-release.list >/dev/null
    apt_update_seguro
    apt_instalar brave-browser
}

instalar_edge() {
    verificar_internet || return 1
    local url="https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_current_amd64.deb"
    instalar_deb_remoto "$url" "/tmp/edge.deb" "Microsoft Edge"
}

instalar_vivaldi() {
    verificar_internet || return 1
    local url="https://downloads.vivaldi.com/stable/vivaldi-stable_current_amd64.deb"
    instalar_deb_remoto "$url" "/tmp/vivaldi.deb" "Vivaldi"
}

instalar_opera() {
    verificar_internet || return 1
    local url="https://download.opera.com/download/get/?id=41527&location=410&nothanks=yes"
    instalar_deb_remoto "$url" "/tmp/opera.deb" "Opera"
}

# ----------------------------------------------------------------------
# Apps de Desenvolvimento
# ----------------------------------------------------------------------

menu_apps_desenvolvimento() {
    local op_dev=""
    clear
    echo -e "${COR_HEADER}========================================${COR_RESET}"
    echo -e "${COR_HEADER}  FERRAMENTAS DE DESENVOLVIMENTO${COR_RESET}"
    echo -e "${COR_HEADER}========================================${COR_RESET}"
    echo ""
    echo "1. Git + build-essential"
    echo "2. Visual Studio Code (snap)"
    echo "3. Docker"
    echo "4. Todos"
    echo "0. Voltar"
    read -rp "Escolha [0-4]: " op_dev

    case "$op_dev" in
        1) apt_instalar git build-essential ;;
        2)
            if command -v snap &>/dev/null; then
                executar_comando_seguro "Instalar VS Code (snap)" snap install code --classic
            else
                log_mensagem "ERRO" "Snap não instalado. Use o menu Gerenciar Flatpak/Snap primeiro."
            fi
            ;;
        3)
            apt_instalar docker.io
            executar_comando_seguro "Ativar Docker" systemctl enable --now docker
            if [[ -n "${SUDO_USER:-}" ]]; then
                usermod -aG docker "$SUDO_USER"
                log_mensagem "INFO" "Usuário '$SUDO_USER' adicionado ao grupo docker."
            fi
            ;;
        4)
            apt_instalar git build-essential docker.io
            executar_comando_seguro "Ativar Docker" systemctl enable --now docker
            if [[ -n "${SUDO_USER:-}" ]]; then
                usermod -aG docker "$SUDO_USER"
                log_mensagem "INFO" "Usuário '$SUDO_USER' adicionado ao grupo docker."
            fi
            if command -v snap &>/dev/null; then
                executar_comando_seguro "Instalar VS Code (snap)" snap install code --classic
            else
                log_mensagem "ERRO" "Snap não instalado. VS Code não instalado."
            fi
            ;;
    esac
    pausa
}

# ----------------------------------------------------------------------
# Flatpaks com verificação
# ----------------------------------------------------------------------

declare -A FLATPAK_APT_EQUIVALENTES=(
    ["org.videolan.VLC"]="vlc"
    ["org.gimp.GIMP"]="gimp"
    ["com.visualstudio.code"]="code"
    ["com.spotify.Client"]="spotify-client"
    ["org.onlyoffice.desktopeditors"]="onlyoffice-desktopeditors"
    ["com.bitwarden.desktop"]="bitwarden"
    ["com.anydesk.Anydesk"]="anydesk"
)

verificar_duplicacao() {
    local flatpak_id="$1"
    local apt_pkg="${FLATPAK_APT_EQUIVALENTES[$flatpak_id]}"
    if [[ -n "$apt_pkg" ]] && dpkg -l "$apt_pkg" &>/dev/null 2>&1; then
        log_mensagem "AVISO" "'$apt_pkg' já instalado via APT. Pulando flatpak '$flatpak_id'."
        return 1
    fi
    return 0
}

instalar_flatpaks() {
    log_mensagem "INFO" "=== Flatpaks com verificação de duplicação ==="

    if ! command -v flatpak &>/dev/null; then
        log_mensagem "ERRO" "Flatpak não instalado. Use o menu Gerenciar Flatpak/Snap primeiro."
        pausa
        return
    fi

    local flatpks=(
        "com.bitwarden.desktop"
        "org.videolan.VLC"
        "org.gimp.GIMP"
        "com.spotify.Client"
        "org.onlyoffice.desktopeditors"
    )

    for app in "${flatpks[@]}"; do
        if verificar_duplicacao "$app"; then
            echo -e "${COR_INFO}Instalar $app? (s/N)${COR_RESET}"
            local resp=""
            read -r resp
            [[ "$resp" =~ ^[Ss]$ ]] && \
                executar_comando_seguro "Instalar $app" flatpak install flathub "$app" -y --noninteractive
        fi
    done
    pausa
}

# ----------------------------------------------------------------------
# Manutenção e Limpeza
# ----------------------------------------------------------------------

menu_limpeza() {
    local op_limpeza=""
    while true; do
        clear
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo -e "${COR_HEADER}  LIMPEZA E MANUTENÇÃO${COR_RESET}"
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo "1. Limpeza básica (autoclean, autoremove)"
        echo "2. Limpeza profunda (purge, órfãos)"
        echo "3. Remover kernels antigos"
        echo "4. Limpar cache de pacotes"
        echo "5. Limpar logs antigos"
        echo "6. Limpeza COMPLETA"
        echo "0. Voltar"
        read -rp "Escolha [0-6]: " op_limpeza

        case "$op_limpeza" in
            1)
                executar_comando_seguro "Autoclean" apt-get autoclean -y
                executar_comando_seguro "Autoremove" apt-get autoremove -y
                pausa
                ;;
            2)
                executar_comando_seguro "Autoremove --purge" apt-get autoremove --purge -y
                if command -v deborphan &>/dev/null; then
                    deborphan | xargs -r apt-get remove --purge -y 2>/dev/null || true
                fi
                dpkg -l | awk '/^rc/ {print $2}' | xargs -r dpkg --purge 2>/dev/null || true
                pausa
                ;;
            3)
                remover_kernels_antigos
                pausa
                ;;
            4)
                apt-get clean
                rm -rf /var/cache/apt/archives/*.deb 2>/dev/null
                log_mensagem "SUCESSO" "Cache limpo."
                pausa
                ;;
            5)
                journalctl --vacuum-time=7d 2>/dev/null || true
                find /var/log -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
                log_mensagem "SUCESSO" "Logs antigos removidos."
                pausa
                ;;
            6)
                executar_comando_seguro "Autoclean" apt-get autoclean -y
                executar_comando_seguro "Autoremove --purge" apt-get autoremove --purge -y
                remover_kernels_antigos
                apt-get clean
                journalctl --vacuum-time=7d 2>/dev/null || true
                find /var/log -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
                pausa
                ;;
            0) return ;;
        esac
    done
}

remover_kernels_antigos() {
    local kernel_atual
    kernel_atual=$(get_kernel_version "$(uname -r)")
    local kernels_remover=()

    while IFS= read -r linha; do
        local pkg ver
        pkg=$(echo "$linha" | awk '{print $2}')
        ver=$(echo "$linha" | awk '{print $3}')
        ver=$(get_kernel_version "$ver")
        if [[ "$pkg" =~ ^(linux-image|linux-headers|linux-modules)-[0-9] ]]; then
            [[ "$ver" != "$kernel_atual" ]] && kernels_remover+=("$pkg")
        fi
    done < <(dpkg -l 'linux-image-*' 'linux-headers-*' 'linux-modules-*' 2>/dev/null | grep '^ii')

    if [[ ${#kernels_remover[@]} -eq 0 ]]; then
        log_mensagem "INFO" "Nenhum kernel antigo encontrado."
        return
    fi

    echo "Kernens a remover:"
    printf '  %s\n' "${kernels_remover[@]}"
    if confirmar_acao "Remover estes kernels?"; then
        executar_comando_seguro "Remover kernels" apt-get purge -y "${kernels_remover[@]}"
        executar_comando_seguro "Atualizar GRUB" update-grub
    fi
}

# ----------------------------------------------------------------------
# Ferramentas TI
# ----------------------------------------------------------------------

menu_ferramentas_ti() {
    local op_ti=""
    while true; do
        clear
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo -e "${COR_HEADER}  FERRAMENTAS DO PROFISSIONAL DE TI${COR_RESET}"
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo ""
        echo "--- Diagnóstico e Monitoramento ---"
        echo "1.  Diagnóstico completo de hardware"
        echo "2.  Teste SMART (saúde dos discos)"
        echo "3.  Teste de memória RAM (memtester)"
        echo "4.  CPU Stress Test (stress-ng)"
        echo "5.  Benchmark de disco (hdparm/dd)"
        echo "6.  Dispositivos USB e PCI"
        echo "7.  Informações DMI/BIOS"
        echo "8.  Análise de Boot (systemd-analyze)"
        echo "9.  Saúde da Bateria (notebook)"
        echo ""
        echo "--- Segurança e Integridade ---"
        echo "10. Verificar integridade de pacotes (debsums)"
        echo "11. Varredura de Rootkit (rkhunter/chkrootkit)"
        echo "12. Auditoria de Segurança (lynis)"
        echo ""
        echo "--- Geral ---"
        echo "13. Gerar relatório completo do sistema"
        echo "14. Instalar TODAS as ferramentas de diagnóstico"
        echo "0.  Voltar"
        echo ""
        read -rp "Escolha [0-14]: " op_ti

        case "$op_ti" in
            1) diagnostico_hardware_completo; pausa ;;
            2) teste_smart_discos; pausa ;;
            3) teste_memoria_ram; pausa ;;
            4) stress_test_cpu; pausa ;;
            5) benchmark_disco; pausa ;;
            6) listar_dispositivos_usb_pci; pausa ;;
            7) info_dmi_bios; pausa ;;
            8) analise_boot; pausa ;;
            9) saude_bateria; pausa ;;
            10) verificar_pacotes; pausa ;;
            11) varredura_rootkit; pausa ;;
            12) auditoria_lynis; pausa ;;
            13) gerar_relatorio_pro; pausa ;;
            14) instalar_todas_ferramentas_ti; pausa ;;
            0) return ;;
        esac
    done
}

# ----------------------------------------------------------------------
# Funções auxiliares do menu Ferramentas TI
# ----------------------------------------------------------------------

diagnostico_hardware_completo() {
    echo -e "${COR_DESTAQUE}=== CPU ===${COR_RESET}"
    lscpu 2>/dev/null | grep -E "Model name|Socket|Core|Thread|MHz" || echo "lscpu não disponível"
    echo ""
    echo -e "${COR_DESTAQUE}=== Memória ===${COR_RESET}"
    free -h
    echo ""
    echo -e "${COR_DESTAQUE}=== Discos ===${COR_RESET}"
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE 2>/dev/null | grep -vE 'loop|sr[0-9]' || lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
    echo ""
    echo -e "${COR_DESTAQUE}=== GPU ===${COR_RESET}"
    lspci 2>/dev/null | grep -iE 'vga|3d' || echo "lspci não disponível"
    echo ""
    if command -v nvidia-smi &>/dev/null; then
        echo -e "${COR_DESTAQUE}=== NVIDIA SMI ===${COR_RESET}"
        nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used --format=csv,noheader 2>/dev/null || true
        echo ""
    fi
    echo -e "${COR_DESTAQUE}=== Temperaturas ===${COR_RESET}"
    if command -v sensors &>/dev/null; then
        sensors 2>/dev/null | grep -E 'Core|Package|temp|fan|fan[0-9]' || sensors 2>/dev/null || echo "sensors: sem dados"
    else
        echo "lm-sensors não instalado."
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Dispositivos de Áudio ===${COR_RESET}"
    lspci 2>/dev/null | grep -i audio || echo "N/A"
    echo ""
    echo -e "${COR_DESTAQUE}=== USB ===${COR_RESET}"
    lsusb 2>/dev/null | head -15 || echo "lsusb não disponível"
}

teste_smart_discos() {
    if ! command -v smartctl &>/dev/null; then
        apt_instalar smartmontools
    fi
    echo ""
    for disco in $(lsblk -d -o name 2>/dev/null | grep -vE 'loop|sr[0-9]|NAME'); do
        if [[ -b "/dev/$disco" ]]; then
            echo -e "${COR_DESTAQUE}=== SMART /dev/$disco ===${COR_RESET}"
            smartctl -H "/dev/$disco" 2>/dev/null | grep -E 'SMART overall-health|SMART Health Status|PASSED|FAILED' || \
                echo "  SMART não suportado."
            smartctl -A "/dev/$disco" 2>/dev/null | grep -E 'Reallocated_Sector|Pending_Sector|Uncorrectable|Temperature_Celsius|Power_On_Hours' | \
                awk '{printf "  %s: %s\n", $2, $10}' 2>/dev/null || true
            echo ""
        fi
    done
}

teste_memoria_ram() {
    if ! command -v memtester &>/dev/null; then
        apt_instalar memtester
    fi
    echo -e "${COR_INFO}Testando 100MB de RAM (1 iteração)...${COR_RESET}"
    memtester 100M 1 2>/dev/null || echo -e "${COR_ERRO}Teste de memória falhou ou não suportado.${COR_RESET}"
}

stress_test_cpu() {
    if ! command -v stress-ng &>/dev/null; then
        echo -e "${COR_AVISO}stress-ng não instalado. Instalando...${COR_RESET}"
        apt_instalar stress-ng
    fi
    local nucleos
    nucleos=$(nproc 2>/dev/null || echo 2)
    local tempo=30
    echo ""
    echo -e "${COR_AVISO}⚠️  Teste de STRESS na CPU — $nucleos núcleos, ${tempo}s de duração${COR_RESET}"
    echo -e "${COR_AVISO}   O sistema pode ficar lento durante o teste.${COR_RESET}"
    echo ""
    if confirmar_acao "Iniciar stress test?"; then
        echo -e "${COR_INFO}Executando stress-ng com $nucleos workers por ${tempo}s...${COR_RESET}"
        stress-ng --cpu "$nucleos" --cpu-method matrixprod --timeout "${tempo}s" --metrics-brief 2>&1 | tail -5
        echo -e "${COR_SUCESSO}Stress test concluído.${COR_RESET}"
    fi
}

benchmark_disco() {
    local disco_alvo=""
    echo ""
    echo "Discos disponíveis:"
    lsblk -d -o NAME,SIZE,ROTA,MODEL 2>/dev/null | grep -vE 'loop|sr[0-9]' || lsblk -d -o NAME,SIZE
    echo ""
    read -rp "Disco para benchmark (ex: sda, nvme0n1): " disco_alvo
    disco_alvo="/dev/${disco_alvo#/dev/}"
    if [[ ! -b "$disco_alvo" ]]; then
        echo -e "${COR_ERRO}Disco $disco_alvo não encontrado.${COR_RESET}"
        return
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Teste de Leitura (hdparm) ===${COR_RESET}"
    if command -v hdparm &>/dev/null; then
        hdparm -Tt "$disco_alvo" 2>/dev/null || echo "hdparm: teste falhou"
    else
        echo "hdparm não instalado. Instale com 'apt install hdparm'."
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Teste de Escrita (dd) ===${COR_RESET}"
    local ponto_montagem
    ponto_montagem=$(lsblk -no MOUNTPOINT "$disco_alvo" 2>/dev/null | head -1)
    local arquivo_test=""
    if [[ -n "$ponto_montagem" ]] && [[ -w "$ponto_montagem" ]]; then
        local arquivo_test="$ponto_montagem/.bench_ti_$$"
        dd if=/dev/zero of="$arquivo_test" bs=1M count=1024 conv=fdatasync 2>&1 | tail -1
        dd if="$arquivo_test" of=/dev/null bs=1M count=1024 2>&1 | tail -1
        rm -f "$arquivo_test"
    else
        # Testa na home do root
        local arquivo_test="/tmp/.bench_ti_$$"
        dd if=/dev/zero of="$arquivo_test" bs=1M count=512 conv=fdatasync 2>&1 | tail -1
        dd if="$arquivo_test" of=/dev/null bs=1M count=512 2>&1 | tail -1
        rm -f "$arquivo_test"
        echo -e "${COR_AVISO}(teste realizado em /tmp, pode não refletir performance real do disco)${COR_RESET}"
    fi
}

listar_dispositivos_usb_pci() {
    echo -e "${COR_DESTAQUE}=== Dispositivos PCI ===${COR_RESET}"
    lspci -nn 2>/dev/null | head -30 || echo "lspci não disponível"
    echo ""
    echo -e "${COR_DESTAQUE}=== Dispositivos USB ===${COR_RESET}"
    lsusb 2>/dev/null | head -20 || echo "lsusb não disponível"
    echo ""
    echo -e "${COR_DESTAQUE}=== Módulos de Kernel Carregados ===${COR_RESET}"
    lsmod 2>/dev/null | head -20 || echo "lsmod não disponível"
}

info_dmi_bios() {
    echo -e "${COR_DESTAQUE}=== BIOS/UEFI ===${COR_RESET}"
    if command -v dmidecode &>/dev/null; then
        dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release' | head -5
    else
        echo "dmidecode não instalado."
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Placa Mãe ===${COR_RESET}"
    if command -v dmidecode &>/dev/null; then
        dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer|Product|Version' | head -3
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Chassis / Sistema ===${COR_RESET}"
    if command -v dmidecode &>/dev/null; then
        dmidecode -t system 2>/dev/null | grep -E 'Manufacturer|Product|Version|Serial' | head -5
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Memória Física (slots) ===${COR_RESET}"
    if command -v dmidecode &>/dev/null; then
        dmidecode -t memory 2>/dev/null | grep -E 'Size|Type|Speed|Manufacturer|Locator' | head -20
    fi
}

analise_boot() {
    echo -e "${COR_DESTAQUE}=== Tempo Total de Boot ===${COR_RESET}"
    systemd-analyze 2>/dev/null || echo "systemd-analyze não disponível"
    echo ""
    echo -e "${COR_DESTAQUE}=== Serviços Mais Lentos no Boot (top 10) ===${COR_RESET}"
    systemd-analyze blame 2>/dev/null | head -10 || true
    echo ""
    echo -e "${COR_DESTAQUE}=== Cadeia de Dependências do Boot ===${COR_RESET}"
    systemd-analyze critical-chain 2>/dev/null | head -15 || true
    echo ""
    echo -e "${COR_DESTAQUE}=== Serviços Falhos ===${COR_RESET}"
    systemctl --failed 2>/dev/null || echo "Nenhum serviço falho."
    echo ""
    echo -e "${COR_DESTAQUE}=== Unidades Não Necessárias (sugestão) ===${COR_RESET}"
    systemctl list-units --type=service --state=running 2>/dev/null | \
        grep -iE 'bluetooth|cups|avahi-daemon|whoopsie|modemmanager' | \
        awk '{print "  Sugestão: desabilitar " $1}' || echo "  Nenhuma sugestão."
}

saude_bateria() {
    echo -e "${COR_DESTAQUE}=== Informações da Bateria ===${COR_RESET}"
    if command -v upower &>/dev/null; then
        local bateria
        bateria=$(upower -e 2>/dev/null | grep -i battery | head -1)
        if [[ -n "$bateria" ]]; then
            upower -i "$bateria" 2>/dev/null
        else
            echo "Nenhuma bateria detectada."
        fi
    elif command -v acpi &>/dev/null; then
        acpi -V 2>/dev/null || echo "acpi não retornou dados."
    else
        echo "Nenhuma ferramenta de bateria disponível. Instale upower ou acpi."
    fi
    echo ""
    if [[ -d /sys/class/power_supply ]]; then
        for bat in /sys/class/power_supply/BAT*; do
            if [[ -d "$bat" ]]; then
                echo "Bateria $(basename "$bat"):"
                echo "  Modelo: $(cat "$bat/model_name" 2>/dev/null || echo N/A)"
                echo "  Capacity: $(cat "$bat/capacity" 2>/dev/null || echo N/A)%"
                echo "  Status: $(cat "$bat/status" 2>/dev/null || echo N/A)"
                echo "  Tecnologia: $(cat "$bat/technology" 2>/dev/null || echo N/A)"
                echo "  Ciclos: $(cat "$bat/cycle_count" 2>/dev/null || echo N/A)"
                echo "  Saúde: $(cat "$bat/charge_full_design" 2>/dev/null || echo N/A) / $(cat "$bat/charge_full" 2>/dev/null || echo N/A)"
                echo ""
            fi
        done
    fi
}

verificar_pacotes() {
    if ! command -v debsums &>/dev/null; then
        apt_instalar debsums
    fi
    echo ""
    echo -e "${COR_INFO}Verificando integridade dos pacotes instalados...${COR_RESET}"
    debsums -s 2>/dev/null | tee /tmp/pacotes_corrompidos.txt
    local total
    total=$(wc -l < /tmp/pacotes_corrompidos.txt 2>/dev/null || echo 0)
    if [[ "$total" -eq 0 ]]; then
        echo -e "${COR_SUCESSO}Nenhum pacote corrompido encontrado.${COR_RESET}"
    else
        echo -e "${COR_ERRO}$total pacote(s) corrompido(s) encontrado(s). Verifique /tmp/pacotes_corrompidos.txt${COR_RESET}"
    fi
}

varredura_rootkit() {
    echo ""
    echo -e "${COR_DESTAQUE}=== Varredura de Rootkit ===${COR_RESET}"
    local ferramenta=""
    if command -v rkhunter &>/dev/null; then
        ferramenta="rkhunter"
        echo -e "${COR_INFO}Usando rkhunter...${COR_RESET}"
        rkhunter --check --skip-keypress --report-warnings-only 2>/dev/null | tail -20 || true
    elif command -v chkrootkit &>/dev/null; then
        ferramenta="chkrootkit"
        echo -e "${COR_INFO}Usando chkrootkit...${COR_RESET}"
        chkrootkit -q 2>/dev/null | grep -v 'not infected' | head -20 || echo "Nenhuma infecção detectada."
    else
        echo -e "${COR_AVISO}Nenhuma ferramenta de rootkit instalada. Deseja instalar?"
        if confirmar_acao "Instalar rkhunter?"; then
            apt_instalar rkhunter
            rkhunter --check --skip-keypress --report-warnings-only 2>/dev/null | tail -20 || true
        fi
    fi
    echo ""
    echo -e "${COR_DESTAQUE}=== Verificação de Processos Suspeitos ===${COR_RESET}"
    ps aux 2>/dev/null | awk '$3>50.0 || $4>50.0 {print "  ALTA: " $11 " CPU:" $3 "% MEM:" $4 "%"}' | head -5 || true
    echo ""
    echo -e "${COR_DESTAQUE}=== Portas Aberta Suspeitas ===${COR_RESET}"
    ss -tlnp 2>/dev/null | awk '{print $4}' | grep -vE '127.0.0.1|::1|0.0.0.0' | head -10 || true
}

auditoria_lynis() {
    echo ""
    if command -v lynis &>/dev/null; then
        echo -e "${COR_AVISO}⚠️  A auditoria lynis pode levar vários minutos.${COR_RESET}"
        if confirmar_acao "Iniciar auditoria?"; then
            echo -e "${COR_INFO}Executando lynis audit system...${COR_RESET}"
            lynis audit system --quick 2>/dev/null | tail -30 || true
            echo ""
            echo -e "${COR_DESTAQUE}Resumo:${COR_RESET}"
            grep -E 'hardening_index|warnings|suggestions' /var/log/lynis-report.dat 2>/dev/null | \
                sed 's/^/  /' || echo "  Relatório não encontrado em /var/log/lynis-report.dat"
        fi
    else
        echo -e "${COR_AVISO}lynis não instalado. Deseja instalar?"
        if confirmar_acao "Instalar lynis?"; then
            apt_instalar lynis
            if confirmar_acao "Executar auditoria agora?"; then
                lynis audit system --quick 2>/dev/null | tail -30 || true
            fi
        fi
    fi
}

instalar_todas_ferramentas_ti() {
    log_mensagem "INFO" "Instalando todas as ferramentas de diagnóstico..."
    apt_instalar inxi hwinfo lshw htop neofetch smartmontools memtester stress-ng \
        dmidecode nmap net-tools dnsutils debsums deborphan testdisk sysstat iotop \
        hdparm lm-sensors upower acpi rkhunter chkrootkit lynis usbutils pciutils \
        nvme-cli
    log_mensagem "SUCESSO" "Todas as ferramentas TI foram instaladas."
}

gerar_relatorio_pro() {
    local relat="/tmp/relatorio-ti-${TIMESTAMP}.txt"
    {
        echo "============================================"
        echo " RELATÓRIO COMPLETO DO SISTEMA"
        echo " Gerado em: $(date)"
        echo "============================================"
        echo ""
        echo "--- Informações Básicas ---"
        echo "Hostname: $(hostname)"
        if command -v lsb_release &>/dev/null; then
            echo "Sistema: $(lsb_release -ds 2>/dev/null)"
        elif [[ -f /etc/os-release ]]; then
            echo "Sistema: $(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d= -f2 | tr -d '\"')"
        fi
        echo "Kernel: $(uname -r)"
        echo "Arquitetura: $(uname -m)"
        echo "Uptime: $(uptime -p 2>/dev/null || uptime)"
        echo ""
        echo "--- Hardware - CPU ---"
        lscpu 2>/dev/null | grep -E 'Model name|Socket|Core|Thread|MHz|CPU max|CPU min' || echo "lscpu não disponível"
        echo ""
        echo "--- Hardware - Memória ---"
        free -h
        echo ""
        echo "--- Hardware - Discos ---"
        lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL 2>/dev/null || lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE
        echo ""
        echo "--- Hardware - GPU ---"
        lspci 2>/dev/null | grep -iE 'vga|3d' || echo "lspci não disponível"
        if command -v nvidia-smi &>/dev/null; then
            nvidia-smi --query-gpu=name,temperature.gpu,utilization.gpu,memory.used --format=csv,noheader 2>/dev/null || true
        fi
        echo ""
        echo "--- Hardware - Temperaturas ---"
        sensors 2>/dev/null | grep -E 'Core|Package|temp|fan' | head -10 || echo "sensors não disponível"
        echo ""
        echo "--- Rede - Interfaces ---"
        ip -br addr 2>/dev/null || ip addr
        echo ""
        echo "--- Rede - Roteamento ---"
        ip route 2>/dev/null || route -n 2>/dev/null
        echo ""
        echo "--- Rede - DNS ---"
        grep -E '^nameserver' /etc/resolv.conf 2>/dev/null || echo "resolv.conf não encontrado"
        echo ""
        echo "--- BIOS / Placa Mãe ---"
        if command -v dmidecode &>/dev/null; then
            dmidecode -t bios 2>/dev/null | grep -E 'Vendor|Version|Release'
            dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer|Product'
            dmidecode -t system 2>/dev/null | grep -E 'Manufacturer|Product|Serial'
        fi
        echo ""
        echo "--- Serviços Falhos ---"
        systemctl --failed 2>/dev/null || echo "Nenhum"
        echo ""
        echo "--- Análise de Boot ---"
        systemd-analyze 2>/dev/null || echo "systemd-analyze não disponível"
        systemd-analyze blame 2>/dev/null | head -5 || true
        echo ""
        echo "--- Erros no dmesg (últimos 20) ---"
        dmesg 2>/dev/null | grep -iE 'error|fail|warn' | tail -20 || echo "dmesg não disponível"
        echo ""
        echo "--- Pacotes Instalados ---"
        dpkg -l 2>/dev/null | grep '^ii' | wc -l | xargs -I{} echo "Total: {} pacotes"
        echo ""
        echo "--- Snap/Flatpak ---"
        echo "Snaps:"; snap list 2>/dev/null | tail -n +2 | wc -l || echo "  snap não disponível"
        echo "Flatpaks:"; flatpak list --app 2>/dev/null | wc -l || echo "  flatpak não disponível"
    } > "$relat"

    log_mensagem "SUCESSO" "Relatório salvo em $relat ($(wc -l < "$relat") linhas)"
    echo -e "${COR_INFO}Conteúdo do relatório:${COR_RESET}"
    cat "$relat"
}

# ----------------------------------------------------------------------
# Gerenciamento Flatpak/Snap
# ----------------------------------------------------------------------

menu_flatpak_snap() {
    local op_fs=""
    while true; do
        clear
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo -e "${COR_HEADER}  GERENCIAR FLATPAK E SNAP${COR_RESET}"
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo "1. Instalar Flatpak + Flathub"
        echo "2. Instalar Snap (snapd)"
        echo "3. Remover Flatpak (completo)"
        echo "4. Remover Snap (completo)"
        echo "5. Atualizar Flatpaks"
        echo "6. Atualizar Snaps"
        echo "7. Status/Informações"
        echo "0. Voltar"
        read -rp "Escolha [0-7]: " op_fs

        case "$op_fs" in
            1)
                apt_instalar flatpak
                flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
                pausa
                ;;
            2)
                if command -v snap &>/dev/null; then
                    log_mensagem "AVISO" "Snap já instalado."
                else
                    apt_instalar snapd
                    executar_comando_seguro "Ativar snapd" systemctl enable --now snapd
                fi
                pausa
                ;;
            3)
                if confirmar_acao "Remover TODOS os Flatpaks e o serviço?"; then
                    if command -v flatpak &>/dev/null; then
                        flatpak list --app --columns=application 2>/dev/null | while read -r app; do
                            [[ -n "$app" ]] && flatpak uninstall --noninteractive "$app" 2>/dev/null
                        done
                        flatpak uninstall --unused --noninteractive 2>/dev/null || true
                        flatpak remote-delete --force flathub 2>/dev/null || true
                    fi
                    executar_comando_seguro "Remover flatpak" apt-get purge --auto-remove -y flatpak
                    rm -rf /var/lib/flatpak ~/.local/share/flatpak /root/.local/share/flatpak 2>/dev/null
                    log_mensagem "SUCESSO" "Flatpak removido."
                fi
                pausa
                ;;
            4)
                if confirmar_acao "Remover TODOS os snaps e o serviço?"; then
                    if command -v snap &>/dev/null; then
                        snap list 2>/dev/null | awk 'NR>1 {print $1}' | while read -r sp; do
                            [[ -n "$sp" ]] && snap remove --purge "$sp" 2>/dev/null
                        done
                        systemctl stop snapd 2>/dev/null || true
                        systemctl disable snapd 2>/dev/null || true
                    fi
                    executar_comando_seguro "Remover snapd" apt-get purge --auto-remove -y snapd
                    rm -rf /var/snap /snap ~/snap /root/snap /var/cache/snapd 2>/dev/null
                    log_mensagem "SUCESSO" "Snap removido."
                fi
                pausa
                ;;
            5)
                if command -v flatpak &>/dev/null; then
                    executar_comando_seguro "Atualizar Flatpaks" flatpak update -y --noninteractive
                else
                    log_mensagem "ERRO" "Flatpak não instalado."
                fi
                pausa
                ;;
            6)
                if command -v snap &>/dev/null; then
                    executar_comando_seguro "Atualizar Snaps" snap refresh
                else
                    log_mensagem "ERRO" "Snap não instalado."
                fi
                pausa
                ;;
            7)
                echo -e "${COR_DESTAQUE}=== FLATPAK ===${COR_RESET}"
                if command -v flatpak &>/dev/null; then
                    flatpak --version
                    echo "Repositórios:"
                    flatpak remotes 2>/dev/null || echo "  Nenhum."
                    echo "Apps:"
                    flatpak list --app 2>/dev/null || echo "  Nenhum."
                else
                    echo "Flatpak não instalado."
                fi
                echo -e "\n${COR_DESTAQUE}=== SNAP ===${COR_RESET}"
                if command -v snap &>/dev/null; then
                    snap version 2>/dev/null
                    echo "Snaps:"
                    snap list 2>/dev/null || echo "  Nenhum."
                else
                    echo "Snap não instalado."
                fi
                pausa
                ;;
            0) return ;;
        esac
    done
}

# ----------------------------------------------------------------------
# Diagnóstico de Rede (Menu completo)
# ----------------------------------------------------------------------

menu_rede() {
    local op_rede=""
    local alvo=""
    local porta=""

    while true; do
        clear
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo -e "${COR_HEADER}  DIAGNÓSTICO DE REDE${COR_RESET}"
        echo -e "${COR_HEADER}========================================${COR_RESET}"
        echo ""
        echo "1. Informações completas de rede"
        echo "2. Teste de conectividade (ping)"
        echo "3. Rota de pacotes (traceroute)"
        echo "4. MTR (ping + traceroute combinado)"
        echo "5. Escaneamento de portas"
        echo "6. Análise de DNS"
        echo "7. Monitorar conexões ativas"
        echo "8. Teste de velocidade/banda"
        echo "9. Captura de pacotes (tcpdump)"
        echo "10. Análise de WiFi"
        echo "11. Firewall e regras"
        echo "12. Debug HTTP/Web (headers)"
        echo "13. Relatório completo de rede"
        echo "14. Instalar TODAS ferramentas de rede"
        echo "0. Voltar"
        echo ""
        read -rp "Escolha [0-14]: " op_rede

        case "$op_rede" in
            1)
                echo -e "\n${COR_DESTAQUE}=== Interfaces de Rede ===${COR_RESET}"
                ip -br addr 2>/dev/null || ifconfig -a 2>/dev/null || ip addr
                echo ""
                echo -e "${COR_DESTAQUE}=== Tabela de Roteamento ===${COR_RESET}"
                ip route 2>/dev/null || route -n 2>/dev/null
                echo ""
                echo -e "${COR_DESTAQUE}=== Gateway Padrão ===${COR_RESET}"
                ip route 2>/dev/null | grep default || route -n 2>/dev/null | grep '^0.0.0.0'
                echo ""
                echo -e "${COR_DESTAQUE}=== DNS Configurado ===${COR_RESET}"
                if [[ -f /etc/resolv.conf ]]; then
                    grep -E '^nameserver|^search|^domain' /etc/resolv.conf | head -10
                fi
                resolvectl status 2>/dev/null || systemd-resolve --status 2>/dev/null || true
                echo ""
                echo -e "${COR_DESTAQUE}=== ARP Table ===${COR_RESET}"
                ip neigh 2>/dev/null || arp -a 2>/dev/null
                echo ""
                echo -e "${COR_DESTAQUE}=== Velocidade e Link das Interfaces ===${COR_RESET}"
                for iface in $(ip -o link show | awk -F': ' '{print $2}' | grep -v lo); do
                    echo -n "  $iface: "
                    ethtool "$iface" 2>/dev/null | grep -i speed || echo "ethtool não disponível"
                done
                pausa
                ;;
            2)
                echo ""
                read -rp "Endereço/IP para ping (deixe vazio para 8.8.8.8): " alvo
                alvo="${alvo:-8.8.8.8}"
                echo -e "\n${COR_INFO}Pingando $alvo (Ctrl+C para parar)...${COR_RESET}"
                ping -c 5 -W 3 "$alvo" 2>&1 || echo -e "${COR_ERRO}Falha no ping.${COR_RESET}"
                pausa
                ;;
            3)
                echo ""
                read -rp "Endereço/IP para traceroute (deixe vazio para 8.8.8.8): " alvo
                alvo="${alvo:-8.8.8.8}"
                if command -v traceroute &>/dev/null; then
                    echo -e "\n${COR_INFO}Traceroute para $alvo...${COR_RESET}"
                    traceroute -n "$alvo" 2>&1 | head -30
                else
                    echo -e "${COR_AVISO}traceroute não instalado. Instalando...${COR_RESET}"
                    apt_instalar traceroute
                    traceroute -n "$alvo" 2>&1 | head -30
                fi
                pausa
                ;;
            4)
                echo ""
                read -rp "Endereço/IP para MTR (deixe vazio para 8.8.8.8): " alvo
                alvo="${alvo:-8.8.8.8}"
                if command -v mtr &>/dev/null; then
                    echo -e "\n${COR_INFO}MTR para $alvo (modo relatório, 10 pacotes)...${COR_RESET}"
                    mtr -r -c 10 "$alvo" 2>&1
                else
                    echo -e "${COR_AVISO}mtr não instalado. Instalando...${COR_RESET}"
                    apt_instalar mtr-tiny
                    mtr -r -c 10 "$alvo" 2>&1
                fi
                pausa
                ;;
            5)
                echo ""
                echo "1. Portas LOCAIS em escuta"
                echo "2. Escanear IP/domínio remoto"
                echo "0. Voltar"
                read -rp "Escolha [0-2]: " op_rede
                case "$op_rede" in
                    1)
                        echo -e "\n${COR_DESTAQUE}=== Portas em Escuta (TCP) ===${COR_RESET}"
                        ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
                        echo ""
                        echo -e "${COR_DESTAQUE}=== Portas em Escuta (UDP) ===${COR_RESET}"
                        ss -ulnp 2>/dev/null || netstat -ulnp 2>/dev/null
                        ;;
                    2)
                        read -rp "IP ou domínio para escanear: " alvo
                        [[ -z "$alvo" ]] && { echo "Cancelado."; pausa; continue; }
                        read -rp "Porta(s) (ex: 22,80,443 ou 1-1000): " porta
                        if command -v nmap &>/dev/null; then
                            echo -e "${COR_INFO}Escaneando $alvo...${COR_RESET}"
                            if [[ -n "$porta" ]]; then
                                nmap -sS -T4 -p "$porta" "$alvo" 2>&1 | head -40
                            else
                                nmap -sS -T4 --top-ports 100 "$alvo" 2>&1 | head -40
                            fi
                        else
                            echo -e "${COR_AVISO}nmap não instalado. Usando nc...${COR_RESET}"
                            apt_instalar nmap 2>/dev/null && nmap -sS -T4 --top-ports 100 "$alvo" 2>&1 | head -40 || \
                                echo "Instale o nmap para escaneamento completo."
                        fi
                        ;;
                esac
                pausa
                ;;
            6)
                echo ""
                read -rp "Domínio para consulta DNS (ex: google.com): " alvo
                [[ -z "$alvo" ]] && { echo "Cancelado."; pausa; continue; }
                echo -e "\n${COR_DESTAQUE}=== Registros A (IPv4) ===${COR_RESET}"
                dig +short A "$alvo" 2>/dev/null || nslookup "$alvo" 2>/dev/null | head -10
                echo -e "${COR_DESTAQUE}=== Registros AAAA (IPv6) ===${COR_RESET}"
                dig +short AAAA "$alvo" 2>/dev/null || true
                echo -e "${COR_DESTAQUE}=== Registros MX ===${COR_RESET}"
                dig +short MX "$alvo" 2>/dev/null || true
                echo -e "${COR_DESTAQUE}=== Registros NS ===${COR_RESET}"
                dig +short NS "$alvo" 2>/dev/null || true
                echo -e "${COR_DESTAQUE}=== WHOIS ===${COR_RESET}"
                whois "$alvo" 2>/dev/null | head -15 || echo "whois não instalado."
                pausa
                ;;
            7)
                echo ""
                echo -e "${COR_DESTAQUE}=== Conexões TCP Ativas ===${COR_RESET}"
                ss -tuna 2>/dev/null | head -40 || netstat -tuna 2>/dev/null | head -40
                echo ""
                echo -e "${COR_DESTAQUE}=== Processos Escutando Portas ===${COR_RESET}"
                ss -tlnp 2>/dev/null | head -30 || netstat -tlnp 2>/dev/null | head -30
                echo ""
                echo -e "${COR_DESTAQUE}=== Estatísticas de Rede ===${COR_RESET}"
                nstat 2>/dev/null | head -20 || netstat -s 2>/dev/null | head -20
                echo ""
                if command -v lsof &>/dev/null; then
                    echo -e "${COR_DESTAQUE}=== Arquivos Abertos por Rede (lsof -i) ===${COR_RESET}"
                    lsof -i 2>/dev/null | head -30
                fi
                echo ""
                echo -e "${COR_DESTAQUE}=== Tráfego por Interface ===${COR_RESET}"
                ip -s link 2>/dev/null | grep -E '^[0-9]|RX|TX' | head -20
                pausa
                ;;
            8)
                echo ""
                echo "1. Teste de velocidade (speedtest-cli)"
                echo "2. Teste iperf3 (cliente)"
                echo "3. Latência para múltiplos hosts"
                echo "0. Voltar"
                read -rp "Escolha [0-3]: " op_rede
                case "$op_rede" in
                    1)
                        if command -v speedtest-cli &>/dev/null || command -v speedtest &>/dev/null; then
                            echo -e "${COR_INFO}Executando speedtest...${COR_RESET}"
                            speedtest-cli --simple 2>/dev/null || speedtest --simple 2>/dev/null || \
                                echo "speedtest não disponível."
                        else
                            echo -e "${COR_AVISO}Instalando speedtest-cli...${COR_RESET}"
                            apt_instalar speedtest-cli && speedtest-cli --simple 2>/dev/null || \
                                echo "Falha ao executar speedtest."
                        fi
                        ;;
                    2)
                        read -rp "Servidor iperf3: " alvo
                        [[ -z "$alvo" ]] && { echo "Cancelado."; pausa; continue; }
                        if command -v iperf3 &>/dev/null; then
                            iperf3 -c "$alvo" -t 10 2>&1
                        else
                            apt_instalar iperf3 && iperf3 -c "$alvo" -t 10 2>&1 || \
                                echo "Falha ao executar iperf3."
                        fi
                        ;;
                    3)
                        echo -e "${COR_INFO}Testando latência para hosts comuns...${COR_RESET}"
                        for host in "8.8.8.8" "1.1.1.1" "google.com" "localhost"; do
                            local media
                            media=$(ping -c 3 -W 2 "$host" 2>/dev/null | tail -1 | awk '{print $4}' | cut -d'/' -f2)
                            echo "  $host: ${media:-falhou} ms"
                        done
                        ;;
                esac
                pausa
                ;;
            9)
                echo ""
                echo "1. Capturar tráfego HTTP (porta 80)"
                echo "2. Capturar tráfego DNS (porta 53)"
                echo "3. Capturar tudo na interface principal"
                echo "4. Capturar para arquivo (análise posterior)"
                echo "0. Voltar"
                read -rp "Escolha [0-4]: " op_rede
                if ! command -v tcpdump &>/dev/null; then
                    echo -e "${COR_AVISO}tcpdump não instalado. Instalando...${COR_RESET}"
                    apt_instalar tcpdump
                fi
                local iface_principal
                iface_principal=$(ip route 2>/dev/null | grep default | awk '{print $5}' | head -1)
                iface_principal="${iface_principal:-eth0}"
                case "$op_rede" in
                    1)
                        echo -e "${COR_INFO}Capturando HTTP em $iface_principal (10 pacotes)...${COR_RESET}"
                        tcpdump -i "$iface_principal" -c 10 -nn port 80 2>&1 | head -20
                        ;;
                    2)
                        echo -e "${COR_INFO}Capturando DNS em $iface_principal (10 pacotes)...${COR_RESET}"
                        tcpdump -i "$iface_principal" -c 10 -nn port 53 2>&1 | head -20
                        ;;
                    3)
                        echo -e "${COR_INFO}Capturando tudo em $iface_principal (20 pacotes)...${COR_RESET}"
                        tcpdump -i "$iface_principal" -c 20 -nn 2>&1 | head -40
                        ;;
                    4)
                        local arquivo_cap="/tmp/captura-${TIMESTAMP}.pcap"
                        echo -e "${COR_INFO}Capturando 100 pacotes para $arquivo_cap...${COR_RESET}"
                        tcpdump -i "$iface_principal" -c 100 -nn -w "$arquivo_cap" 2>&1
                        echo -e "${COR_SUCESSO}Captura salva em: $arquivo_cap${COR_RESET}"
                        echo -e "${COR_INFO}Use 'tcpdump -r $arquivo_cap -nn' para analisar.${COR_RESET}"
                        ;;
                esac
                pausa
                ;;
            10)
                echo ""
                echo -e "${COR_DESTAQUE}=== Interfaces WiFi Detectadas ===${COR_RESET}"
                local wifis=()
                while IFS= read -r iface; do
                    wifis+=("$iface")
                done < <(iwconfig 2>/dev/null | grep -o '^[^ ]*' || nmcli device status 2>/dev/null | grep wifi | awk '{print $1}')
                if [[ ${#wifis[@]} -eq 0 ]]; then
                    echo "Nenhuma interface WiFi detectada."
                else
                    for w in "${wifis[@]}"; do
                        echo -e "\n${COR_INFO}Interface: $w${COR_RESET}"
                        iwconfig "$w" 2>/dev/null | grep -E 'ESSID|Mode|Frequency|Signal|Bit Rate' || true
                    done
                    echo ""
                    if command -v nmcli &>/dev/null; then
                        echo -e "${COR_DESTAQUE}=== Redes Disponíveis (nmcli) ===${COR_RESET}"
                        nmcli dev wifi list 2>/dev/null | head -20
                    elif command -v iwlist &>/dev/null; then
                        for w in "${wifis[@]}"; do
                            echo -e "${COR_INFO}Redes em $w:${COR_RESET}"
                            iwlist "$w" scan 2>/dev/null | grep -E 'ESSID|Signal|Encryption|Channel' | head -30
                        done
                    fi
                fi
                echo ""
                echo -e "${COR_DESTAQUE}=== Informações nmcli geral ===${COR_RESET}"
                nmcli general status 2>/dev/null || true
                nmcli connection show 2>/dev/null | head -10 || true
                pausa
                ;;
            11)
                echo ""
                echo -e "${COR_DESTAQUE}=== Status UFW ===${COR_RESET}"
                if command -v ufw &>/dev/null; then
                    ufw status verbose 2>/dev/null
                else
                    echo "UFW não instalado."
                fi
                echo ""
                echo -e "${COR_DESTAQUE}=== Regras iptables (filter) ===${COR_RESET}"
                if command -v iptables &>/dev/null; then
                    iptables -L -n -v 2>/dev/null | head -40
                else
                    echo "iptables não instalado."
                fi
                echo ""
                if command -v nft &>/dev/null; then
                    echo -e "${COR_DESTAQUE}=== Regras nftables ===${COR_RESET}"
                    nft list ruleset 2>/dev/null | head -40 || true
                fi
                echo ""
                echo -e "${COR_DESTAQUE}=== Portas Redirecionadas (NAT) ===${COR_RESET}"
                iptables -t nat -L -n 2>/dev/null | head -20 || true
                pausa
                ;;
            12)
                echo ""
                read -rp "URL para debug HTTP (ex: https://google.com): " alvo
                [[ -z "$alvo" ]] && { echo "Cancelado."; pausa; continue; }
                echo -e "\n${COR_DESTAQUE}=== Headers HTTP ===${COR_RESET}"
                curl -sI -L --max-time 10 "$alvo" 2>&1 | head -30 || \
                    echo -e "${COR_ERRO}Falha ao acessar $alvo${COR_RESET}"
                echo ""
                echo -e "${COR_DESTAQUE}=== Tempo total (curl -w) ===${COR_RESET}"
                curl -s -o /dev/null -w "  Tempo de conexão: %{time_connect}s\n  TTFB: %{time_starttransfer}s\n  Total: %{time_total}s\n  HTTP: %{http_code}\n  DNS: %{time_namelookup}s\n" \
                    --max-time 10 "$alvo" 2>&1 || true
                pausa
                ;;
            13)
                gerar_relatorio_rede
                pausa
                ;;
            14)
                echo -e "${COR_INFO}Instalando ferramentas de rede...${COR_RESET}"
                apt_instalar net-tools dnsutils traceroute mtr-tiny nmap tcpdump iperf3 \
                    speedtest-cli whois ethtool nmap iw wireless-tools rfkill curl wget \
                    lsof nftables
                log_mensagem "SUCESSO" "Ferramentas de rede instaladas."
                pausa
                ;;
            0) return ;;
        esac
    done
}

gerar_relatorio_rede() {
    local relat="/tmp/relatorio-rede-${TIMESTAMP}.txt"
    {
        echo "Relatório Completo de Rede - $(date)"
        echo "Hostname: $(hostname)"
        echo "========================================"
        echo ""
        echo "--- Interfaces ---"
        ip -br addr 2>/dev/null || ip addr
        echo ""
        echo "--- Roteamento ---"
        ip route 2>/dev/null
        echo ""
        echo "--- DNS ---"
        grep -E '^nameserver' /etc/resolv.conf 2>/dev/null || echo "resolv.conf não encontrado"
        resolvectl status 2>/dev/null || systemd-resolve --status 2>/dev/null || true
        echo ""
        echo "--- ARP ---"
        ip neigh 2>/dev/null || arp -a 2>/dev/null
        echo ""
        echo "--- Portas em Escuta ---"
        ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null
        echo ""
        echo "--- Conexões Ativas ---"
        ss -tuna 2>/dev/null | head -40 || netstat -tuna 2>/dev/null | head -40
        echo ""
        echo "--- Tabela de Firewall (iptables) ---"
        iptables -L -n -v 2>/dev/null || echo "iptables não disponível"
        echo ""
        echo "--- Latência (ping 8.8.8.8) ---"
        ping -c 5 -W 3 8.8.8.8 2>/dev/null | tail -3
        echo ""
        echo "--- WiFi ---"
        iwconfig 2>/dev/null || echo "WiFi não disponível"
        echo ""
        echo "--- Estatísticas de Rede ---"
        nstat 2>/dev/null | head -30 || netstat -s 2>/dev/null | head -30
    } > "$relat"
    log_mensagem "SUCESSO" "Relatório de rede salvo em $relat"
    echo -e "${COR_INFO}Conteúdo do relatório:${COR_RESET}"
    cat "$relat"
}

# ----------------------------------------------------------------------
# Menu Principal
# ----------------------------------------------------------------------

exibir_banner() {
    clear
    echo -e "${COR_HEADER}╔══════════════════════════════════════════════════╗${COR_RESET}"
    echo -e "${COR_HEADER}║  SETUP PÓS-FORMAÇÃO PRO v${SCRIPT_VERSAO}               ║${COR_RESET}"
    echo -e "${COR_HEADER}║  Canivete Suíço do Profissional de TI           ║${COR_RESET}"
    echo -e "${COR_HEADER}╚══════════════════════════════════════════════════╝${COR_RESET}"
    echo ""
    if command -v lsb_release &>/dev/null; then
        echo -e "Sistema: ${COR_INFO}$(lsb_release -ds 2>/dev/null)${COR_RESET}"
    elif [[ -f /etc/os-release ]]; then
        echo -e "Sistema: ${COR_INFO}$(grep -E '^PRETTY_NAME=' /etc/os-release | cut -d= -f2 | tr -d '\"')${COR_RESET}"
    fi
    echo -e "Kernel: ${COR_INFO}$(uname -r)${COR_RESET}"
    echo -e "GPU(s): ${COR_INFO}$(detectar_gpu)${COR_RESET}"
    echo -e "Log: ${COR_INFO}${ARQUIVO_LOG}${COR_RESET}"
    echo ""
}

exibir_menu_principal() {
    echo -e "${BOLD}Escolha o modo de operação:${COR_RESET}"
    echo ""
    echo "1. Setup COMPLETO (Pós-formatação)"
    echo "2. Otimizações do Sistema"
    echo "3. Customização (Temas, HiDPI, Codecs)"
    echo "4. Drivers de Vídeo (GPU)"
    echo "5. Instalar Navegadores"
    echo "6. Ferramentas de Desenvolvimento"
    echo "7. Instalar Flatpaks"
    echo "8. Manutenção e Limpeza"
    echo "9. Ferramentas do Profissional de TI"
    echo "10. Gerar Relatório Completo"
    echo "11. Gerenciar Flatpak/Snap"
    echo "12. Diagnóstico de Rede"
    echo "13. Segurança e Auditoria"
    echo "0. Sair"
    echo ""
}

principal() {
    for arg in "$@"; do
        case "$arg" in
            --strict) MODO_STRICT=true ;;
            --verbose) MODO_VERBOSE=true ;;
            --pro) MODO_PROFISSIONAL=true ;;
            --help|-h)
                echo "Uso: sudo $0 [OPÇÕES]"
                echo "  --strict    Para em qualquer erro"
                echo "  --verbose   Logs detalhados"
                echo "  --pro       Adiciona ferramentas de TI no setup completo"
                exit 0
                ;;
        esac
    done

    verificar_root

    local opcao_principal=""

    while true; do
        exibir_banner
        exibir_menu_principal
        read -rp "Opção [0-13]: " opcao_principal

        case "$opcao_principal" in
            1)
                log_mensagem "INFO" "=== INICIANDO SETUP COMPLETO ==="
                verificar_internet || { pausa; continue; }
                configurar_locale
                configurar_firewall
                configurar_tlp_notebook
                configurar_zram
                otimizar_kernel
                otimizar_ssd
                configurar_grub
                instalar_codecs_fontes
                configurar_hidpi
                instalar_temas
                configurar_timeshift
                menu_drivers_gpu
                menu_navegadores
                menu_apps_desenvolvimento
                instalar_flatpaks
                if [[ "$MODO_PROFISSIONAL" == true ]]; then
                    apt_instalar inxi hwinfo smartmontools memtester debsums deborphan
                fi
                executar_comando_seguro "Upgrade do sistema" apt-get upgrade -y
                executar_comando_seguro "Autoremove final" apt-get autoremove -y
                limpar_sistema
                gerar_relatorio_pro
                log_mensagem "SUCESSO" "SETUP COMPLETO FINALIZADO!"
                pausa
                ;;
            2)
                configurar_locale
                configurar_firewall
                configurar_tlp_notebook
                configurar_zram
                otimizar_kernel
                otimizar_ssd
                configurar_grub
                pausa
                ;;
            3)
                instalar_codecs_fontes
                configurar_hidpi
                instalar_temas
                pausa
                ;;
            4)
                menu_drivers_gpu
                ;;
            5)
                menu_navegadores
                ;;
            6)
                menu_apps_desenvolvimento
                ;;
            7)
                instalar_flatpaks
                ;;
            8)
                menu_limpeza
                ;;
            9)
                menu_ferramentas_ti
                ;;
            10)
                gerar_relatorio_pro
                pausa
                ;;
            11)
                menu_flatpak_snap
                ;;
            12)
                menu_rede
                ;;
            13)
                varredura_rootkit
                echo ""
                auditoria_lynis
                pausa
                ;;
            0)
                log_mensagem "INFO" "Script finalizado pelo usuário."
                exit 0
                ;;
            *)
                log_mensagem "ERRO" "Opção inválida. Tente novamente."
                pausa
                ;;
        esac
    done
}

principal "$@"
