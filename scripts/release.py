#!/usr/bin/env python3
"""Prepare notarized universal releases, then publish binaries before the Sparkle feed.

Secrets stay in Keychain: lilagents-notary and Sparkle account lilagents.
No commits, tags or pushes are made to the source checkout. Public distribution
uses a separate repository containing only releases, documentation and appcast.
"""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

from package_dmg import digest, sign_universal_app

ROOT = Path(__file__).resolve().parents[1]
REPO = 'IlanSalviano/lilagents-releases'
FEED = f'https://raw.githubusercontent.com/{REPO}/main/appcast.xml'
IDENTITY = 'Developer ID Application: Ilan Salviano (22CZXFP6W7)'
DERIVED = ROOT / 'build/RemoteReleaseDerivedData'
AMIT = ['walk-amit-01.mov', 'special-amit-flow-01.mov',
        'special-amit-point-01.mov', 'amit-animation-layouts.json']
os.environ.setdefault('DEVELOPER_DIR', '/Applications/Xcode.app/Contents/Developer')


def run(*args):
    result = subprocess.run([str(a) for a in args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{args[0]} failed ({result.returncode}):\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}')
    return result.stdout.strip()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def sparkle_tool(name):
    for derived in [DERIVED, ROOT / 'build/DerivedData']:
        path = derived / 'SourcePackages/artifacts/sparkle/Sparkle/bin' / name
        if path.is_file():
            return path
    raise RuntimeError('Build first to resolve Sparkle tools')


def source_hash():
    h = hashlib.sha256()
    files = list((ROOT / 'LilAgents').rglob('*')) + [
        ROOT / 'lil-agents.xcodeproj/project.pbxproj', Path(__file__),
        ROOT / 'scripts/package_dmg.py']
    for path in sorted(files):
        if path.is_file() and path.name != '.DS_Store' and 'Art' not in path.parts:
            h.update(str(path.relative_to(ROOT)).encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def notarize(path, work, label):
    """Persist submission IDs and poll them on retry, without submitting twice."""
    state_path = work / f'{label}-submission.json'
    sha = digest(path)
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state['sha256'] != sha:
            raise RuntimeError(f'{label} changed after submission; use a new release directory')
    else:
        state = json.loads(run('xcrun', 'notarytool', 'submit', path,
                               '--keychain-profile', 'lilagents-notary', '--output-format', 'json'))
        state['sha256'] = sha
        save(state_path, state)
    print(f'{label}: Apple submission {state["id"]}', flush=True)
    for _ in range(180):
        status = json.loads(run('xcrun', 'notarytool', 'info', state['id'],
                                '--keychain-profile', 'lilagents-notary', '--output-format', 'json'))
        save(work / f'{label}-status.json', status)
        if status['status'] == 'Accepted':
            run('xcrun', 'notarytool', 'log', state['id'], '--keychain-profile',
                'lilagents-notary', work / f'{label}-apple-log.json')
            return state['id']
        if status['status'] != 'In Progress':
            raise RuntimeError(f'Apple rejected {label}: {status}')
        time.sleep(10)
    raise RuntimeError('Apple still processing; rerun the same command to resume')


def prepare(args):
    version, build = args.version, args.build
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or build < 7:
        raise ValueError('Use a semantic version and a build number >= 7')
    source_info = plistlib.loads((ROOT / 'LilAgents/Info.plist').read_bytes())
    public_key = run(sparkle_tool('generate_keys'), '--account', 'lilagents', '-p')
    if source_info['SUFeedURL'] != FEED or source_info['SUPublicEDKey'] != public_key:
        raise RuntimeError('Source feed/key do not match the release channel')
    work = ROOT / 'build/releases' / version
    work.mkdir(parents=True, exist_ok=True)
    output = ROOT / 'dist/releases' / version
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'release.json'
    fingerprint = dict(version=version, build=build, withoutAmit=args.without_amit,
                       sourceHash=source_hash())
    notes = args.notes_file.read_text(encoding='utf-8').strip() if args.notes_file else None
    if notes is not None:
        if not notes:
            raise ValueError('Release notes must not be empty')
        fingerprint['releaseNotesSHA256'] = hashlib.sha256(notes.encode()).hexdigest()
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['inputs'] != fingerprint or digest(output / manifest['file']) != manifest['sha256']:
            raise RuntimeError('Existing release differs; never overwrite a published version')
        print(f'Reusing verified release: {manifest_path}', flush=True)
        return
    staging = work / 'staging'
    app = staging / 'lil agents.app'
    signed = work / 'signed.json'
    if signed.exists():
        if json.loads(signed.read_text())['inputs'] != fingerprint:
            raise RuntimeError('Inputs changed during release; use a new release directory')
        run('codesign', '--verify', '--deep', '--strict', app)
    else:
        print(f'Building {version} ({build}), Amit={not args.without_amit}', flush=True)
        with (work / 'build.log').open('w') as log:
            result = subprocess.run(['xcodebuild', '-project', 'lil-agents.xcodeproj',
                '-scheme', 'LilAgents', '-configuration', 'Release', '-derivedDataPath', str(DERIVED),
                '-destination', 'generic/platform=macOS', 'ARCHS=arm64 x86_64',
                'ONLY_ACTIVE_ARCH=NO', 'CODE_SIGNING_ALLOWED=NO',
                f'MARKETING_VERSION={version}', f'CURRENT_PROJECT_VERSION={build}', 'build'],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'Build failed; see {work / "build.log"}')
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir()
        run('ditto', DERIVED / 'Build/Products/Release/lil agents.app', app)
        resources = app / 'Contents/Resources'
        if args.without_amit:
            for name in AMIT:
                (resources / name).unlink()
        shutil.copy2(ROOT / 'LICENSE', resources / 'LICENSE.txt')
        architectures = sign_universal_app(app, IDENTITY)
        save(signed, dict(inputs=fingerprint, architectures=architectures))
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info['CFBundleVersion'] != str(build) or info['CFBundleShortVersionString'] != version:
        raise RuntimeError('Built version mismatch')
    if info['SUFeedURL'] != FEED or info['SUPublicEDKey'] != public_key:
        raise RuntimeError('Built updater configuration mismatch')
    resources = app / 'Contents/Resources'
    if any((resources / name).exists() != (not args.without_amit) for name in AMIT):
        raise RuntimeError('Incorrect Amit resource set')
    app_zip = work / 'app.zip'
    if not app_zip.exists():
        run('ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', app, app_zip)
    app_submission = notarize(app_zip, work, 'app')
    run('xcrun', 'stapler', 'staple', app)
    run('xcrun', 'stapler', 'validate', app)
    run('spctl', '--assess', '--type', 'execute', '--verbose=2', app)
    if not (staging / 'Applications').is_symlink():
        (staging / 'Applications').symlink_to('/Applications')
    shutil.copy2(ROOT / 'LICENSE', staging / 'LICENSE.txt')
    readme = ('lil agents — edição personalizada\n\nmacOS 14+, Intel e Apple Silicon.\n'
              'Arraste lil agents.app para Applications, abra o app e ejete o disco.\n'
              'Use o menu do app > Check for Updates… para buscar novas versões.\n'
              'As atualizações incluem os novos personagens. Sounds controla as falas.\n'
              'Para conversar com IA, instale e autentique o CLI do provedor desejado.\n'
              'Credenciais e conversas desta máquina não estão incluídas.\n\n'
              'App e DMG assinados e notarizados pela Apple.\n'
              f'Downloads: https://github.com/{REPO}/releases\n'
              'Baseado em ryanstephen/lil-agents, licença MIT em LICENSE.txt.\n')
    (staging / 'LEIA-ME.txt').write_text(readme)
    dmg = work / f'lil-agents-{version}-universal.dmg'
    if not dmg.exists():
        run('hdiutil', 'create', '-volname', f'lil agents {version}', '-srcfolder', staging,
            '-fs', 'HFS+', '-format', 'UDZO', '-imagekey', 'zlib-level=9', dmg)
        run('codesign', '--sign', IDENTITY, '--timestamp', dmg)
    # Stapling changes the DMG bytes. Keep the submitted image for safe resumption.
    dmg_submission = notarize(dmg, work, 'dmg')
    final = output / dmg.name
    shutil.copy2(dmg, final)
    run('xcrun', 'stapler', 'staple', final)
    run('xcrun', 'stapler', 'validate', final)
    run('codesign', '--verify', '--strict', final)
    run('hdiutil', 'verify', final)
    run('spctl', '--assess', '--type', 'open', '--context', 'context:primary-signature',
        '--verbose=2', final)
    mount = work / 'mount'
    mount.mkdir(exist_ok=True)
    run('hdiutil', 'attach', final, '-readonly', '-nobrowse', '-mountpoint', mount)
    try:
        mounted = mount / 'lil agents.app'
        run('codesign', '--verify', '--deep', '--strict', mounted)
        run('xcrun', 'stapler', 'validate', mounted)
        mounted_info = plistlib.loads((mounted / 'Contents/Info.plist').read_bytes())
        if mounted_info != info or os.readlink(mount / 'Applications') != '/Applications':
            raise RuntimeError('Mounted installer mismatch')
        movie_hashes = {p.name: digest(p) for p in resources.glob('*.mov')}
        for name, sha in movie_hashes.items():
            if digest(mounted / 'Contents/Resources' / name) != sha:
                raise RuntimeError(f'Packaged movie mismatch: {name}')
        if any((mounted / 'Contents/Resources' / name).exists() != (not args.without_amit) for name in AMIT):
            raise RuntimeError('Packaged Amit resource mismatch')
    finally:
        run('hdiutil', 'detach', mount)
    note = ('<h2>Atualizações remotas prontas</h2><p>Versão de teste sem Amit. '
            'Use Check for Updates… para instalar a versão que adiciona o personagem.</p>'
            if args.without_amit else '<h2>Amit chegou ao Dock</h2><p>Novo personagem com '
            'personalidade própria, caminhada, soco no ar com “Lets Flow!” e gesto de '
            'apontar com “Let’s make work flow!”. As falas respeitam a opção Sounds.</p>')
    if notes is not None:
        note = ''.join('<p>' + html.escape(paragraph).replace('\n', '<br>') + '</p>'
                       for paragraph in notes.split('\n\n'))
        (output / 'release-notes.md').write_text(notes + '\n', encoding='utf-8')
    final.with_suffix('.html').write_text(note)
    run(sparkle_tool('generate_appcast'), '--account', 'lilagents', '--maximum-deltas', '0',
        '--download-url-prefix', f'https://github.com/{REPO}/releases/download/v{version}/', output)
    feed = ET.parse(output / 'appcast.xml')
    ns = {'s': 'http://www.andymatuschak.org/xml-namespaces/sparkle'}
    item = feed.find('./channel/item')
    enclosure = item.find('enclosure')
    if item.findtext('s:version', namespaces=ns) != str(build):
        raise RuntimeError('Appcast build mismatch')
    signature = enclosure.attrib['{' + ns['s'] + '}edSignature']
    run(sparkle_tool('sign_update'), '--account', 'lilagents', '--verify', final, signature)
    sha = digest(final)
    final.with_suffix('.dmg.sha256').write_text(f'{sha}  {final.name}\n')
    manifest = dict(inputs=fingerprint, version=version, build=build, includesAmit=not args.without_amit,
        file=final.name, sha256=sha, bytes=final.stat().st_size, edSignature=signature,
        publicKey=public_key, feedURL=FEED, downloadURL=enclosure.attrib['url'],
        notarized=True, appSubmission=app_submission, dmgSubmission=dmg_submission,
        architectures=json.loads(signed.read_text())['architectures'], movieChecksums=movie_hashes,
        verified=['Developer ID', 'Apple app ticket', 'Apple DMG ticket', 'Gatekeeper',
                  'mounted resources', 'universal binaries', 'Sparkle signature', 'appcast build'])
    save(manifest_path, manifest)
    print(f'Ready: {final}', flush=True)


def put_content(name, content, message):
    """GitHub Contents API: update only the distribution repo's explicit files."""
    result = subprocess.run(['gh', 'api', f'repos/{REPO}/contents/{name}'],
                            capture_output=True, text=True)
    body = dict(message=message, content=base64.b64encode(content).decode(), branch='main')
    if result.returncode == 0:
        current = json.loads(result.stdout)
        if base64.b64decode(current['content']) == content:
            return
        body['sha'] = current['sha']
    elif '404' not in result.stderr and 'Not Found' not in result.stdout:
        raise RuntimeError(result.stderr)
    result = subprocess.run(['gh', 'api', '--method', 'PUT', f'repos/{REPO}/contents/{name}',
                             '--input', '-'], input=json.dumps(body), capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)


def validate_feed(output, manifest):
    """Reject stale or edited feeds before any publication side effects."""
    ns = '{http://www.andymatuschak.org/xml-namespaces/sparkle}'
    xml = ET.parse(output / 'appcast.xml')
    items = xml.findall('./channel/item')
    if len(items) != 1:
        raise RuntimeError('Expected exactly one newly prepared release in the feed')
    item = items[0]
    enclosure = item.find('enclosure')
    expected_url = f'https://github.com/{REPO}/releases/download/v{manifest["version"]}/{manifest["file"]}'
    if (item.findtext(ns + 'version') != str(manifest['build']) or
        item.findtext(ns + 'shortVersionString') != manifest['version'] or
        enclosure is None or enclosure.get('url') != expected_url or
        enclosure.get('length') != str(manifest['bytes']) or
        enclosure.get(ns + 'edSignature') != manifest['edSignature'] or
        manifest['downloadURL'] != expected_url or manifest['feedURL'] != FEED):
        raise RuntimeError('Appcast does not match the verified release manifest')


def publish(args):
    output = ROOT / 'dist/releases' / args.version
    manifest = json.loads((output / 'release.json').read_text())
    file = output / manifest['file']
    if digest(file) != manifest['sha256'] or not manifest['notarized']:
        raise RuntimeError('Release artifact no longer matches verification')
    validate_feed(output, manifest)
    run(sparkle_tool('sign_update'), '--account', 'lilagents', '--verify', file, manifest['edSignature'])
    result = subprocess.run(['gh', 'repo', 'view', REPO, '--json', 'name'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Create and review the public distribution repository before publishing')
    tag = 'v' + args.version
    result = subprocess.run(['gh', 'release', 'view', tag, '--repo', REPO, '--json', 'isDraft,assets'],
                            capture_output=True, text=True)
    notes = output / 'release-notes.md'
    if not notes.exists():
        notes.write_text(f'lil agents {args.version} (build {manifest["build"]})\n\n'
        + ('Adiciona Amit, com os especiais “Lets Flow!” e “Let’s make work flow!”.\n'
           if manifest['includesAmit'] else 'Versão inicial para testar a atualização remota. Não inclui Amit.\n')
        + '\nDMG universal (Intel e Apple Silicon), assinado e notarizado pela Apple. macOS 14+.\n'
          'Arraste o app para Aplicativos. Use Check for Updates… no menu para atualizar.\n')
    if result.returncode:
        run('gh', 'release', 'create', tag, file, str(file) + '.sha256', '--repo', REPO,
            '--draft', '--title', f'lil agents {args.version}', '--notes-file', notes)
        run('gh', 'release', 'edit', tag, '--repo', REPO, '--draft=false', '--latest')
    elif json.loads(result.stdout)['isDraft']:
        run('gh', 'release', 'upload', tag, file, str(file) + '.sha256', '--repo', REPO, '--clobber')
        run('gh', 'release', 'edit', tag, '--repo', REPO, '--draft=false', '--latest')
    # Fetch anonymously, as an installed client will. Verify every byte BEFORE feed publication.
    for attempt in range(6):
        try:
            h = hashlib.sha256()
            with urllib.request.urlopen(manifest['downloadURL'], timeout=120) as response:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    h.update(block)
            if h.hexdigest() != manifest['sha256']:
                raise RuntimeError('Remote binary checksum mismatch; feed was not updated')
            break
        except OSError:
            if attempt == 5:
                raise
            time.sleep(5)
    if args.update_feed:
        # Prevent accidentally rolling the advertised build backwards.
        current = subprocess.run(['gh', 'api', f'repos/{REPO}/contents/appcast.xml'],
                                 capture_output=True, text=True)
        if current.returncode == 0:
            xml = ET.fromstring(base64.b64decode(json.loads(current.stdout)['content']))
            builds = [int(e.text) for e in xml.findall('.//{http://www.andymatuschak.org/xml-namespaces/sparkle}version')]
            if builds and max(builds) > manifest['build']:
                raise RuntimeError('Refusing to downgrade the published feed')
        put_content('appcast.xml', (output / 'appcast.xml').read_bytes(),
                    f'Publish verified update {args.version} ({manifest["build"]})')
        shutil.copy2(output / 'appcast.xml', ROOT / 'appcast.xml')
    save(output / 'published.json', dict(downloadURL=manifest['downloadURL'],
        remoteChecksumVerified=True, feedPublished=args.update_feed))
    print(f'Published: {manifest["downloadURL"]}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--version', required=True)
    prep.add_argument('--build', type=int, required=True)
    prep.add_argument('--without-amit', action='store_true')
    prep.add_argument('--notes-file', type=Path, help='Release notes for GitHub and the Sparkle update dialog')
    pub = sub.add_parser('publish')
    pub.add_argument('--version', required=True)
    pub.add_argument('--update-feed', action='store_true')
    args = parser.parse_args()
    (prepare if args.command == 'prepare' else publish)(args)


if __name__ == '__main__':
    main()
