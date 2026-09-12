"""Compila o LYNX Atlas como aplicativo standalone para Windows."""

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "LYNX Atlas"
EXECUTABLE_NAME = "LYNXAtlas"
BUILD_DEPENDENCIES = {
    "nuitka": "Nuitka",
    "ordered_set": "ordered-set",
}


def _run(command: list[str], cwd: Path) -> None:
    print("\nComando de compilação:\n  " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def _create_windows_icon(source: Path, destination: Path) -> Path:
    """Cria o ICO do executável/instalador usando o PNG do projeto."""
    from PySide6.QtGui import QImage

    destination.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(str(source))
    if image.isNull() or not image.save(str(destination), "ICO"):
        raise RuntimeError(f"Não foi possível converter {source.name} para ICO")
    return destination


def _package_zip(output_dir: Path) -> None:
    dist_candidates = (
        output_dir / f"{EXECUTABLE_NAME}.dist",
        output_dir / "main.dist",
    )
    dist_dir = next((path for path in dist_candidates if path.is_dir()), None)
    if dist_dir is None:
        print("AVISO: diretório .dist não encontrado; o ZIP não pôde ser criado.")
        return
    archive = Path(shutil.make_archive(
        str(output_dir / f"{EXECUTABLE_NAME}-Windows"), "zip", dist_dir
    ))
    print(f"Pacote portátil criado: {archive}")


def build_app() -> int:
    if platform.system() != "Windows":
        print("Este script deve ser executado no Windows. Para Linux, use o Flatpak.")
        return 2

    missing = [
        package for module, package in BUILD_DEPENDENCIES.items()
        if importlib.util.find_spec(module) is None
    ]
    if missing:
        print(
            "Dependências de compilação ausentes: " + ", ".join(missing) + "\n"
            f'Execute: "{sys.executable}" -m pip install -U ' + " ".join(missing)
        )
        return 2

    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "build" / "nuitka-windows"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        icon = _create_windows_icon(base_dir / "icone.png", base_dir / "build" / "icone.ico")
        command = [
            sys.executable,
            "-m", "nuitka",
            "--standalone",
            "--enable-plugin=pyside6",
            "--include-qt-plugins=imageformats,platforms,styles",
            "--include-package=core",
            f"--include-data-dir={base_dir / 'ui'}=ui",
            f"--include-data-files={base_dir / 'icone.png'}=icone.png",
            f"--include-data-files={base_dir / 'LICENSE'}=LICENSE",
            f"--include-data-files={base_dir / 'README.md'}=README.md",
            f"--include-data-files={base_dir / 'THIRD_PARTY_NOTICES.md'}=THIRD_PARTY_NOTICES.md",
            f"--include-data-dir={base_dir / 'licenses'}=licenses",
            "--include-module=encodings",
            "--follow-imports",
            "--clang",
            "--lto=no",
            f"--jobs={max(1, os.cpu_count() or 1)}",
            "--show-progress",
            "--assume-yes-for-downloads",
            "--remove-output",
            f"--output-dir={output_dir}",
            f"--output-filename={EXECUTABLE_NAME}",
            "--windows-console-mode=disable",
            f"--windows-icon-from-ico={icon}",
            str(base_dir / "main.py"),
        ]
        print(f"Compilando {APP_NAME} para Windows...")
        _run(command, base_dir)
        _package_zip(output_dir)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Falha durante a compilação ou empacotamento: {exc}")
        return 1

    print("Compilação concluída. Agora compile instalador.iss no Inno Setup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_app())
