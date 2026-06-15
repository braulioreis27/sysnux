# AGENTS.md

## Estrutura

- `pos-formatacao_linux.sh` — Script Bash original (1852 linhas). Fonte de verdade para lógica de sistema.
- `Sysnux/` — Projeto Python/PySide6 com interface gráfica. Portabilidade do script original.
- `Sysnux/main.py` — Entrypoint. Checa root e relança via `pkexec` se necessário.
- `Sysnux/sysnux/modules/` — Lógica portada do Bash, um arquivo por domínio.
- `Sysnux/sysnux/ui/main_window.py` — GUI principal com 12 páginas em QStackedWidget + sidebar.

## Comandos essenciais

```bash
# Ativar ambiente virtual
source Sysnux/venv/bin/activate

# Executar em desenvolvimento (abre janela)
python3 Sysnux/main.py

# Compilar executável standalone (65MB)
Sysnux/build.sh
# Resultado: Sysnux/dist/Sysnux

# Executar o binário compilado com root
pkexec env DISPLAY=$DISPLAY ./Sysnux/dist/Sysnux
```

## Arquitetura

- **GUI**: PySide6 (Qt for Python). Tema escuro customizado via stylesheets.
- **Threading**: Cada operação é um generator Python executado em `QThread` via `TaskRunner`. A GUI nunca bloqueia.
- **Elevação de privilégios**: O app solicita root via `pkexec` no startup. Todas as operações de sistema assumem root. O ambiente gráfico é preservado exportando `DISPLAY`, `XAUTHORITY`, `XDG_RUNTIME_DIR`.
- **Console**: Widget customizado `OutputConsole` com cores por nível (`[OK]`, `[ERRO]`, `[AVISO]`, `[INFO]`).

## Módulos (Sysnux/sysnux/modules/)

| Arquivo | Domínio |
|---|---|
| `system.py` | Detecção de hardware/distro/kernel/rede |
| `optimizations.py` | Kernel, SSD, GRUB, ZRAM, TLP, firewall, limpeza |
| `packages.py` | APT, codecs, temas, navegadores, dev tools, Flatpak/Snap |
| `gpu.py` | Drivers NVIDIA/AMD/Intel com suporte a Optimus |
| `tools.py` | Diagnóstico, SMART, RAM, stress, benchmark, boot, rootkit, relatório |

## Convenções

- Funções de módulo são **generators** — `yield` strings de progresso para a GUI.
- `run_command(cmd)` para execução síncrona. `TaskRunner(generator)` para assíncrona.
- `apt_install(pkg_str)` definida em `packages.py` — instala pacotes APT.
- `check_internet()` pinga 8.8.8.8 e 1.1.1.1.
- Cada página da GUI tem checkboxes e método `_get_*_tasks()` que monta lista de generators.

## Constraints importantes

- Toda operação de sistema precisa de root. O app não funciona sem `pkexec` ou `sudo`.
- A GUI usa `subprocess` para comandos shell — comandos mal formatados podem quebrar.
- PySide6 `setTextColor` não existe (PyQt legado). Usar `QTextCharFormat.setForeground()`.
- O virtual environment (`venv/`) é necessário para desenvolvimento. PEP 668 bloqueia `pip install --system`.
- O script Bash original (`pos-formatacao_linux.sh`) é a referência canônica para implementação de novas features.
