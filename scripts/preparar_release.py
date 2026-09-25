"""Compila aquí los artefactos; la máquina de trabajo solo descarga la release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

RAIZ = Path(__file__).resolve().parents[1]
TARGETS = {
    'windows-x64-baseline': 'cuy-windows-x64.exe',
    'windows-arm64': 'cuy-windows-arm64.exe',
    'darwin-arm64': 'cuy-darwin-arm64',
    'darwin-x64-baseline': 'cuy-darwin-x64',
    'linux-x64-baseline': 'cuy-linux-x64',
    'linux-arm64': 'cuy-linux-arm64',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', help='Versión fija, por ejemplo 0.3.0')
    parser.add_argument('--targets', nargs='+', choices=TARGETS,
                        default=['windows-x64-baseline', 'darwin-arm64'])
    args = parser.parse_args()
    version = args.version.removeprefix('v')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){2}(?:-[A-Za-z0-9.-]+)?', version):
        parser.error('Usá una versión semántica fija.')
    bun = shutil.which('bun')
    if not bun:
        parser.error('Este comando es para el equipo de compilación y requiere Bun.')
    fuente = RAIZ / 'vendor/opencode'
    paquete = fuente / 'packages/opencode'
    salida = RAIZ / 'dist-release' / f'v{version}'
    salida.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'OPENCODE_VERSION': version, 'OPENCODE_CHANNEL': 'cuycli',
           'OPENCODE_RELEASE': ''}
    subprocess.run([bun, 'install', '--frozen-lockfile'], cwd=fuente, env=env, check=True)
    hashes = {}
    for target in args.targets:
        subprocess.run([bun, 'run', 'script/build.ts', f'--target={target}',
                        '--skip-embed-web-ui'], cwd=paquete, env=env, check=True)
        nombre = TARGETS[target]
        origen = paquete / 'dist' / f'opencode-{target}' / 'bin' / (
            'opencode.exe' if target.startswith('windows-') else 'opencode')
        destino = salida / nombre
        shutil.copy2(origen, destino)
        with destino.open('rb') as archivo:
            hashes[nombre] = hashlib.file_digest(archivo, 'sha256').hexdigest()
    manifiesto = salida / 'release.json'
    manifiesto.write_text(json.dumps({'version': f'v{version}', 'sha256': hashes}, indent=2) + '\n')
    print(f'Artefactos y manifiesto: {salida}')
    print('Publicá esos archivos en la release y copiá release.json a la raíz del repo.')


if __name__ == '__main__':
    main()
