 Como usar
# Desenvolvimento
source Sysnux/venv/bin/activate
python3 Sysnux/main.py

# Compilar executável
Sysnux/build.sh

# Rodar o binário compilado
pkexec env DISPLAY=$DISPLAY ./Sysnux/dist/Sysnux