#!/usr/bin/env bash
#
# Script de build do Sysnux
# Gera um executável standalone com PyInstaller
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================="
echo " Build Sysnux - Pós-formatação Linux"
echo "============================================="
echo ""

# Ativar virtual environment
if [[ -d "venv" ]]; then
    echo "[OK] Virtual environment encontrado"
    source venv/bin/activate
else
    echo "[INFO] Criando virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install PySide6 pyinstaller
fi

# Instalar dependências adicionais
if [[ -f "requirements.txt" ]]; then
    pip install -r requirements.txt 2>/dev/null || true
fi

echo ""
echo "[INFO] Gerando executável com PyInstaller..."
echo ""

# Criar diretório de saída
mkdir -p dist

pyinstaller \
    --name "Sysnux" \
    --onefile \
    --windowed \
    --clean \
    --noconfirm \
    --add-data "sysnux:sysnux" \
    --hidden-import "PySide6.QtXml" \
    --hidden-import "sysnux" \
    --hidden-import "sysnux.ui" \
    --hidden-import "sysnux.ui.widgets" \
    --hidden-import "sysnux.modules" \
    --hidden-import "sysnux.utils" \
    --distpath "dist" \
    --workpath "build" \
    main.py

echo ""
echo "============================================="
echo " Build concluído!"
echo " Executável: dist/Sysnux"
echo " Tamanho: $(du -h dist/Sysnux 2>/dev/null | cut -f1)"
echo "============================================="
echo ""
echo "Para executar:"
echo "  ./dist/Sysnux"
echo ""
echo "Para executar com privilégios administrativos:"
echo "  pkexec env DISPLAY=\$DISPLAY ./dist/Sysnux"
echo ""
