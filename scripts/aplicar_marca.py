#!/usr/bin/env python3
"""Aplica a identidade Capsula TI em um checkout do RustDesk (testado com a tag 1.5.3).

Uso (na raiz do código do RustDesk):
    python3 capsulati/scripts/aplicar_marca.py --edicao cliente --plataforma windows \
        --host acesso.exemplo.com.br --key "<conteúdo de id_ed25519.pub>"

Cada alteração confere o texto original e para a compilação com erro claro se o RustDesk
tiver mudado. Nada é aplicado "às cegas".

O que muda:
  1. A configuração da edição (nome, tipo de conexão, servidor e chave) fica EMBUTIDA no
     binário. O cliente não lê custom.txt externo, então nenhum arquivo colocado ao lado do
     executável consegue alterar servidor ou comportamento.
  2. Servidor e chave padrão do código passam a ser os da Capsula TI.
  3. Ícones, logotipos e metadados (Windows e macOS) com a marca Capsula TI.
"""
import argparse, base64, json, os, re, shutil, sys
from pathlib import Path

# O console do Windows no Actions usa cp1252 e não imprime "✓" nem acentos.
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, 'reconfigure'):
        _fluxo.reconfigure(encoding='utf-8', errors='replace')

AQUI = Path(__file__).resolve().parent.parent
TAG_TESTADA = '1.5.3'


class ErroMarca(SystemExit):
    pass


def falhar(msg):
    print(f'::error::{msg}', file=sys.stderr)
    raise ErroMarca(1)


def substituir(caminho, antigo, novo, vezes=1, regex=False):
    p = Path(caminho)
    if not p.is_file():
        falhar(f'Arquivo não encontrado: {caminho}')
    texto = p.read_text(encoding='utf-8')
    if regex:
        achados = len(re.findall(antigo, texto, flags=re.M))
    else:
        achados = texto.count(antigo)
    if achados != vezes:
        falhar(f'{caminho}: esperava {vezes} ocorrência(s) de {antigo!r}, encontrei {achados}. '
               f'O RustDesk mudou; revise scripts/aplicar_marca.py (testado com {TAG_TESTADA}).')
    texto = re.sub(antigo, novo, texto, flags=re.M) if regex else texto.replace(antigo, novo)
    p.write_text(texto, encoding='utf-8')
    print(f'  ✓ {caminho}')


def copiar(origem, destino):
    origem, destino = AQUI / origem, Path(destino)
    if not origem.is_file():
        falhar(f'Arquivo de marca ausente: {origem}')
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origem, destino)
    print(f'  ✓ {destino}')


def carregar_edicao(nome, host, key):
    arq = AQUI / 'edicoes' / f'{nome}.json'
    if not arq.is_file():
        falhar(f'Edição desconhecida: {nome}')
    host = (host or '').strip()
    key = (key or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9.-]+(:\d{1,5})?', host):
        falhar('RUSTDESK_HOST inválido ou vazio. Informe o nome ou IP público do servidor (ex.: acesso.capsulati.com.br).')
    try:
        if len(base64.b64decode(key, validate=True)) != 32:
            raise ValueError
    except Exception:
        falhar('RUSTDESK_KEY inválida. Use o conteúdo de /opt/capsulati-remote/data/id_ed25519.pub (44 caracteres).')
    bruto = arq.read_text(encoding='utf-8').replace('{{HOST}}', host).replace('{{KEY}}', key)
    dados = json.loads(bruto)
    meta, custom = dados['capsulati'], dados['custom']
    app = custom.get('app-name', '')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]{2,30}', app):
        falhar(f'app-name "{app}" inválido: use letras, números e hífen, sem espaços ou acentos.')
    if custom.get('conn-type', '') not in ('', 'incoming', 'outgoing'):
        falhar('conn-type deve ser "incoming", "outgoing" ou vazio.')
    if not re.fullmatch(r'[a-z0-9]+(\.[a-z0-9-]+)+', meta.get('bundle_id', '')):
        falhar('bundle_id inválido.')
    return meta, custom, host, key


def config_embutida(custom):
    Path('src/capsulati_custom.json').write_text(json.dumps(custom, ensure_ascii=False, indent=1), encoding='utf-8')
    print('  ✓ src/capsulati_custom.json')
    # read_custom_client: separa a aplicação da configuração da verificação de assinatura.
    substituir('src/common.rs',
               '    let Ok(mut data) =\n'
               '        serde_json::from_slice::<std::collections::HashMap<String, serde_json::Value>>(&data)\n',
               '    apply_custom_client_json(&data);\n'
               '}\n\n'
               '/// Capsula TI: aplica uma configuração de cliente personalizado já validada.\n'
               'pub fn apply_custom_client_json(data: &[u8]) {\n'
               '    let Ok(mut data) =\n'
               '        serde_json::from_slice::<std::collections::HashMap<String, serde_json::Value>>(data)\n')
    # load_custom_client: usa somente a configuração embutida na compilação.
    substituir('src/common.rs',
               'pub fn load_custom_client() {\n',
               'pub fn load_custom_client() {\n'
               '    // Capsula TI: configuração da edição embutida na compilação. Não lê custom.txt\n'
               '    // externo, para que nenhum arquivo ao lado do executável altere o cliente.\n'
               '    apply_custom_client_json(include_bytes!("capsulati_custom.json"));\n'
               '}\n\n'
               '#[allow(dead_code)]\n'
               'fn load_custom_client_upstream() {\n')


def servidor_padrao(host, key):
    cfg = 'libs/hbb_common/src/config.rs'
    substituir(cfg, 'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];',
               f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{host}"];')
    substituir(cfg, r'^pub const RS_PUB_KEY: &str = "[A-Za-z0-9+/=]{44}";$',
               f'pub const RS_PUB_KEY: &str = "{key}";', regex=True)


def metadados_windows(meta, app):
    nome, empresa = meta['nome_exibicao'], meta['empresa']
    copyright_ = f'Copyright (C) 2026 {empresa}. Baseado no RustDesk (AGPL-3.0).'
    rc = 'flutter/windows/runner/Runner.rc'
    trocas = [
        (r'VALUE "CompanyName", "[^"]*"', f'VALUE "CompanyName", "{empresa}"'),
        (r'VALUE "FileDescription", "[^"]*"', f'VALUE "FileDescription", "{meta["descricao"]}"'),
        (r'VALUE "InternalName", "[^"]*"', f'VALUE "InternalName", "{app}"'),
        (r'VALUE "LegalCopyright", "[^"]*"', f'VALUE "LegalCopyright", "{copyright_}"'),
        (r'VALUE "OriginalFilename", "[^"]*"', f'VALUE "OriginalFilename", "{app}.exe"'),
        (r'VALUE "ProductName", "[^"]*"', f'VALUE "ProductName", "{nome}"'),
    ]
    for antigo, novo in trocas:
        substituir(rc, antigo, novo, regex=True)
    # Cargo.toml: metadados da librustdesk.dll; libs/portable: do instalador .exe que o usuário baixa.
    for toml, arquivo in (('Cargo.toml', f'{app}.exe'), ('libs/portable/Cargo.toml', f'{app}-instalador.exe')):
        substituir(toml, r'^LegalCopyright = ".*"$', f'LegalCopyright = "{copyright_}"', regex=True)
        substituir(toml, r'^ProductName = ".*"$', f'ProductName = "{nome}"\nCompanyName = "{empresa}"', regex=True)
        substituir(toml, r'^FileDescription = ".*"$', f'FileDescription = "{meta["descricao"]}"', regex=True)
        substituir(toml, r'^OriginalFilename = ".*"$', f'OriginalFilename = "{arquivo}"', regex=True)


def metadados_macos(meta, app):
    plist = 'flutter/macos/Runner/Info.plist'
    substituir(plist, '<string>com.carriez.rustdesk</string>', f'<string>{meta["bundle_id"]}</string>')
    # Esquema de link (abre o app pelo painel): o RustDesk usa o nome do app em minúsculas.
    substituir(plist, '\t\t\t\t<string>rustdesk</string>', f'\t\t\t\t<string>{app.lower()}</string>')
    substituir('flutter/macos/Runner/Configs/AppInfo.xcconfig', r'^PRODUCT_COPYRIGHT = .*$',
               f'PRODUCT_COPYRIGHT = Copyright © 2026 {meta["empresa"]}. Baseado no RustDesk (AGPL-3.0).', regex=True)


def icones():
    for nome in ('icon.ico', 'icon.png', 'tray-icon.ico', '32x32.png', '64x64.png', '128x128.png',
                 '128x128@2x.png', 'mac-icon.png', 'mac-tray-light-x2.png', 'mac-tray-dark-x2.png'):
        copiar(f'marca/res/{nome}', f'res/{nome}')
    for nome in ('icon.png', 'icon.ico', 'icon.svg', 'logo.png', 'logo_light.png', 'logo_dark.png'):
        copiar(f'marca/assets/{nome}', f'flutter/assets/{nome}')
    copiar('marca/windows/app_icon.ico', 'flutter/windows/runner/resources/app_icon.ico')
    copiar('marca/macos/AppIcon.icns', 'flutter/macos/Runner/AppIcon.icns')


def exportar(meta, custom):
    """Variáveis para os passos seguintes do GitHub Actions."""
    valores = {
        'CAPSULA_APP': custom['app-name'],
        'CAPSULA_NOME': meta['nome_exibicao'],
        'CAPSULA_BUNDLE_ID': meta['bundle_id'],
        'CAPSULA_CONN_TYPE': custom.get('conn-type', ''),
        'CAPSULA_EMPRESA': meta['empresa'],
        'CAPSULA_EDICAO': meta['edicao'],
    }
    destino = os.environ.get('GITHUB_ENV')
    if destino:
        with open(destino, 'a', encoding='utf-8') as f:
            for k, v in valores.items():
                f.write(f'{k}={v}\n')
    for k, v in valores.items():
        print(f'  {k}={v}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--edicao', required=True, choices=['cliente', 'tecnico', 'rapido'])
    ap.add_argument('--plataforma', required=True, choices=['windows', 'macos', 'todas'])
    ap.add_argument('--host', default=os.environ.get('RUSTDESK_HOST', ''))
    ap.add_argument('--key', default=os.environ.get('RUSTDESK_KEY', ''))
    args = ap.parse_args()
    if not Path('src/common.rs').is_file() or not Path('libs/hbb_common/src/config.rs').is_file():
        falhar('Execute na raiz do código do RustDesk (com submódulos: libs/hbb_common).')
    if Path('src/capsulati_custom.json').exists():
        falhar('A marca já foi aplicada neste checkout. Use um checkout limpo.')
    meta, custom, host, key = carregar_edicao(args.edicao, args.host, args.key)
    print(f'Aplicando a edição {meta["nome_exibicao"]} ({custom["app-name"]}) — servidor {host}')
    config_embutida(custom)
    servidor_padrao(host, key)
    if args.plataforma in ('windows', 'todas'):
        metadados_windows(meta, custom['app-name'])
    if args.plataforma in ('macos', 'todas'):
        metadados_macos(meta, custom['app-name'])
    icones()
    exportar(meta, custom)
    print('Marca aplicada.')


if __name__ == '__main__':
    main()
