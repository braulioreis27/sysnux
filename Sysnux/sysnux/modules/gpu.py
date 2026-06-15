from sysnux.utils.runner import run_command
from sysnux.modules.system import detect_gpu


def menu_drivers_gpu(nvidia_opcao="1", amd_opcao="1", intel_opcao="0"):
    yield "[INFO] Detectando GPUs..."
    gpus = detect_gpu()
    yield f"[INFO] GPUs detectadas: {', '.join(gpus)}"

    if "desconhecida" in gpus and len(gpus) == 1:
        yield "[INFO] Nenhuma GPU dedicada detectada"
        return

    if len(gpus) >= 2 and "nvidia" in gpus and "intel" in gpus:
        yield "[INFO] NVIDIA Optimus detectado!"
        if nvidia_opcao == "1":
            ok, _ = run_command("apt-get install -y nvidia-driver-535 nvidia-prime")
            yield f"{'[OK]' if ok else '[FALHA]'} NVIDIA Prime"
            run_command("prime-select on-demand 2>/dev/null || true")
            yield "[OK] prime-select on-demand"
        elif nvidia_opcao == "2":
            run_command("prime-select intel 2>/dev/null || true")
            yield "[OK] Apenas Intel"
        elif nvidia_opcao == "3":
            ok, _ = run_command("apt-get install -y nvidia-driver-535")
            yield f"{'[OK]' if ok else '[FALHA]'} NVIDIA driver"
            run_command("prime-select nvidia 2>/dev/null || true")
            yield "[OK] Apenas NVIDIA"
        return

    for gpu in gpus:
        if gpu == "nvidia":
            yield "[INFO] Instalando driver NVIDIA..."
            if nvidia_opcao == "1":
                ok, _ = run_command("apt-get install -y nvidia-driver-535")
                yield f"{'[OK]' if ok else '[FALHA]'} NVIDIA 535 (Estável)"
            elif nvidia_opcao == "2":
                ok, _ = run_command("apt-get install -y nvidia-driver-545")
                yield f"{'[OK]' if ok else '[FALHA]'} NVIDIA 545 (Recente)"
            elif nvidia_opcao == "3":
                ok, _ = run_command("apt-get install -y nvidia-driver-535 nvidia-cuda-toolkit")
                yield f"{'[OK]' if ok else '[FALHA]'} NVIDIA 535 + CUDA"
        elif gpu == "amd":
            yield "[INFO] Instalando driver AMD..."
            if amd_opcao == "1":
                ok, _ = run_command("apt-get install -y mesa-vulkan-drivers vulkan-tools mesa-utils")
                yield f"{'[OK]' if ok else '[FALHA]'} Mesa Vulkan AMD"
        elif gpu == "intel":
            if intel_opcao == "1":
                yield "[INFO] Instalando driver Intel..."
                ok, _ = run_command("apt-get install -y intel-media-va-driver")
                yield f"{'[OK]' if ok else '[FALHA]'} Intel Media Driver"

    yield "[SUCESSO] Drivers configurados"
