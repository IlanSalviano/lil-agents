#!/usr/bin/env python3
"""Package a prebuilt universal Release app into a verified, Developer ID-signed DMG.

This does not submit to Apple's notarization service. Only the staged copy is
modified; installed apps and source Info.plist are left alone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile


def run(*args):
    result = subprocess.run([str(arg) for arg in args], check=True, capture_output=True)
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sign_universal_app(app, identity):
    # Sign nested code from the inside out, retaining Sparkle helper entitlements.
    magic = {b'\xcf\xfa\xed\xfe', b'\xce\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'}
    binaries = []
    for path in app.rglob('*'):
        if not path.is_file() or path.is_symlink():
            continue
        with path.open('rb') as stream:
            if stream.read(4) in magic:
                binaries.append(path)
    architectures = {}
    for binary in binaries:
        archs = run('lipo', '-archs', binary).decode().split()
        if not {'arm64', 'x86_64'}.issubset(archs):
            raise RuntimeError(f'Non-universal executable: {binary}: {archs}')
        architectures[str(binary.relative_to(app))] = archs
        run('codesign', '--force', '--options', 'runtime', '--timestamp', '--sign',
            identity, '--preserve-metadata=identifier,entitlements', binary)
    bundles = [p for p in app.rglob('*') if not p.is_symlink() and
               p.is_dir() and p.suffix in {'.app', '.xpc', '.framework'}]
    for bundle in sorted(bundles, key=lambda p: len(p.parts), reverse=True):
        run('codesign', '--force', '--options', 'runtime', '--timestamp', '--sign',
            identity, '--preserve-metadata=identifier,entitlements', bundle)
    run('codesign', '--force', '--options', 'runtime', '--timestamp', '--sign',
        identity, '--entitlements', Path(__file__).resolve().parents[1] /
        'LilAgents/LilAgents.entitlements', app)
    run('codesign', '--verify', '--deep', '--strict', app)
    return architectures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--identity', required=True, help='Developer ID Application identity or fingerprint')
    args = parser.parse_args()
    source = args.app.resolve()
    output = args.output.resolve()
    if not (source / 'Contents/Info.plist').is_file():
        parser.error('A built .app is required')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lilagents-dmg-', dir=output.parent) as temp:
        work = Path(temp)
        staging = work / 'staging'
        staging.mkdir()
        app = staging / source.name
        run('ditto', source, app)
        info_path = app / 'Contents/Info.plist'
        info = plistlib.loads(info_path.read_bytes())
        info['SUEnableAutomaticChecks'] = False
        info['SUAllowsAutomaticUpdates'] = False
        info_path.write_bytes(plistlib.dumps(info))
        (staging / 'Applications').symlink_to('/Applications')
        (staging / 'LEIA-ME.txt').write_text('''lil agents — edição com Bill

Requisitos: macOS Sonoma 14 ou posterior; Mac Intel ou Apple Silicon.

1. Arraste “lil agents.app” para “Applications”.
2. Abra o app pela pasta Aplicativos e ejete este disco.
3. Clique com o botão direito no Bill para escolher “Let's go!” ou
   “Put AI to Work!”. A opção Sounds controla as falas.

Os sete personagens e suas animações estão incluídos. Para conversar com IA,
instale e autentique o CLI do provedor desejado nesse Mac. Credenciais e sessões
do computador de origem não estão incluídas. Não é necessário instalar Xcode.

Esta edição personalizada tem atualizações automáticas desativadas para que uma
versão do projeto original não substitua os personagens personalizados.

O app e o DMG têm assinatura Developer ID, mas este pacote não foi notarizado
pela Apple. Se o macOS bloquear a primeira abertura, siga as instruções oficiais:
https://support.apple.com/pt-br/102445
Em Ajustes do Sistema > Privacidade e Segurança, a opção “Abrir Mesmo Assim”
pode aparecer depois da tentativa de abertura.
''', encoding='utf-8')

        architectures = sign_universal_app(app, args.identity)
        print('Universal app and nested code signed and verified', flush=True)

        image = work / 'installer.dmg'
        run('hdiutil', 'create', '-volname', 'lil agents - Bill', '-srcfolder', staging,
            '-fs', 'HFS+', '-format', 'UDZO', '-imagekey', 'zlib-level=9', image)
        run('codesign', '--sign', args.identity, '--timestamp', image)
        run('codesign', '--verify', '--strict', image)
        run('hdiutil', 'verify', image)
        mount = work / 'mount'
        mount.mkdir()
        run('hdiutil', 'attach', image, '-readonly', '-nobrowse', '-mountpoint', mount)
        try:
            mounted_app = mount / source.name
            run('codesign', '--verify', '--deep', '--strict', mounted_app)
            if os.readlink(mount / 'Applications') != '/Applications':
                raise RuntimeError('Missing Applications shortcut')
            resources = mounted_app / 'Contents/Resources'
            movies = sorted(resources.glob('*.mov'))
            required = {'walk-bill-01.mov', 'special-bill-letsgo-01.mov',
                        'special-bill-ai-01.mov', 'bill-animation-layouts.json'}
            if not all((resources / name).is_file() for name in required):
                raise RuntimeError('Bill assets missing from disk image')
            checksums = {p.name: digest(p) for p in movies}
            for name, checksum in checksums.items():
                if digest(source / 'Contents/Resources' / name) != checksum:
                    raise RuntimeError(f'Animation changed during packaging: {name}')
        finally:
            run('hdiutil', 'detach', mount)
        image.replace(output)
        sha = digest(output)
        output.with_suffix('.dmg.sha256').write_text(f'{sha}  {output.name}\n')
        report = dict(appVersion=info['CFBundleShortVersionString'],
                      minimumMacOS=info['LSMinimumSystemVersion'], architectures=architectures,
                      notarized=False, signed=True, signatureVerified=True, diskImageVerified=True,
                      mountedResourcesVerified=True, movieChecksums=checksums,
                      sha256=sha, bytes=output.stat().st_size, automaticUpdates=False)
        output.with_suffix('.verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f'Created {output} ({output.stat().st_size / 1024 / 1024:.1f} MiB)', flush=True)


if __name__ == '__main__':
    main()
