# Sysnux — Pós-formatação Profissional para Linux

**Sysnux** é uma ferramenta gráfica completa para configurar, otimizar e diagnosticar sistemas Linux pós-formatação. Portabilidade do script Bash `pos-formatacao_linux.sh` para Python com interface gráfica moderna (PySide6).

![Python](https://img.shields.io/badge/Python-3.12-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.11-green)
![Licence](https://img.shields.io/badge/Licen%C3%A7a-GPLv3-red)
![Platform](https://img.shields.io/badge/Plataforma-Linux%20(amd64)-orange)

---

## Funcionalidades

| Categoria | O que faz |
|---|---|
| **Dashboard** | Resumo completo do sistema: CPU, RAM, discos, GPU, rede, uptime |
| **Setup Completo** | Configuração total pós-formatação em um clique |
| **Otimizações** | Kernel (BBR, swappiness), ZRAM, TLP, SSD (fstrim, noatime), GRUB, firewall UFW |
| **Estilo & Codecs** | Codecs restritos, fontes Microsoft, temas Papirus + Orchis, HiDPI |
| **Drivers GPU** | NVIDIA (535/545/CUDA), AMD (Mesa Vulkan), Intel (Media Driver), suporte Optimus |
| **Navegadores** | Chrome, Firefox, Brave, Edge, Vivaldi, Opera |
| **Desenvolvimento** | Git, build-essential, Docker, VS Code (snap) |
| **Flatpak / Snap** | Instalação e configuração de Flatpak + Flathub e Snap |
| **Limpeza** | Autoclean, autoremove, kernels antigos, cache, logs, miniaturas |
| **Segurança** | Varredura rootkit (rkhunter), auditoria Lynis, debsums |
| **Diagnóstico Rede** | Ping, DNS, portas, teste velocidade, regras firewall |
| **Ferramentas TI** | Diagnóstico hardware, SMART, RAM, stress CPU, benchmark disco, análise boot, bateria, relatório completo |

---

## Requisitos

- Linux Ubuntu/Debian (ou derivado)
- Python 3.10+
- PySide6
- Acesso root (via `pkexec`)

---

## Instalação

### Via executável (recomendado)

```bash
# Baixe o binário da página de releases
chmod +x Sysnux
pkexec env DISPLAY=$DISPLAY ./Sysnux
```

### Via fonte (desenvolvimento)

```bash
git clone https://github.com/seu-usuario/sysnux.git
cd sysnux

# Crie o ambiente virtual
python3 -m venv Sysnux/venv
source Sysnux/venv/bin/activate

# Instale dependências
pip install -r Sysnux/requirements.txt

# Execute
python3 Sysnux/main.py
```

---

## Uso

```bash
# Executar com interface gráfica (solicita root automaticamente)
python3 Sysnux/main.py

# OU via binário compilado
pkexec env DISPLAY=$DISPLAY ./Sysnux/dist/Sysnux
```

1. Navegue pelas 12 páginas na sidebar
2. Marque as tarefas desejadas
3. Clique em **Executar**
4. Acompanhe o progresso no console colorido

---

## Estrutura do Projeto

```
Sysnux/
├── main.py              # Entrypoint (checa root, pkexec)
├── build.sh             # Compilação PyInstaller
├── requirements.txt     # Dependências
├── sysnux/
│   ├── modules/
│   │   ├── system.py        # Detecção hardware/distro
│   │   ├── optimizations.py # Kernel, SSD, GRUB, ZRAM, TLP
│   │   ├── packages.py      # APT, codecs, navegadores, dev
│   │   ├── gpu.py           # Drivers NVIDIA/AMD/Intel
│   │   └── tools.py         # Diagnóstico, SMART, stress
│   ├── ui/
│   │   ├── main_window.py   # GUI principal (12 páginas)
│   │   └── widgets/
│   │       └── output_console.py  # Console colorido
│   └── utils/
│       ├── runner.py        # run_command + TaskRunner (QThread)
│       └── logging.py       # Log para /var/log
└── dist/                 # Executável compilado
```

---

## Arquitetura

- **Interface**: PySide6 (Qt for Python) com tema escuro customizado
- **Threading**: Cada operação é um generator executado em `QThread` via `TaskRunner`. A GUI nunca bloqueia
- **Elevação**: `pkexec` no startup para operações root
- **Console**: Widget `OutputConsole` com cores por nível (`[OK]`, `[ERRO]`, `[AVISO]`, `[INFO]`)
- **Módulos**: Funções generator que `yield` strings de progresso para a GUI

---

## Script Original

O script Bash original de 1852 linhas (`pos-formatacao_linux.sh`) serve como referência canônica para implementação de novas features.

---

## Licença

GNU General Public License v3.0 — veja o arquivo [LICENSE](LICENSE).

---

## Autor

**Bráulio Reis**

- Email: braulioreis.ti@gmail.com
- GitHub: [@braulioreis27](https://github.com/braulioreis27)
