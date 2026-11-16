#!/usr/bin/env bash
# Renomeia o RustDesk.app compilado para a edição Capsula TI, assina ad-hoc e gera o .dmg.
# Uso: empacotar_macos.sh <APP> <NOME_EXIBICAO> <BUNDLE_ID> <VERSAO> <ARQ>
# O RustDesk procura /Applications/<APP>.app/Contents/MacOS/<APP>, por isso o pacote e o
# executável precisam ter exatamente o nome do app definido na edição.
set -Eeuo pipefail
APP=$1 NOME=$2 BUNDLE=$3 VERSAO=$4 ARQ=$5
ORIGEM=./flutter/build/macos/Build/Products/Release/RustDesk.app
SAIDA=./SaidaCapsula
DESTINO="$SAIDA/$APP.app"
PB=/usr/libexec/PlistBuddy
[[ -d $ORIGEM ]] || { echo "::error::$ORIGEM não encontrado"; exit 1; }
rm -rf "$SAIDA"; mkdir -p "$SAIDA"
ditto "$ORIGEM" "$DESTINO"
mv "$DESTINO/Contents/MacOS/RustDesk" "$DESTINO/Contents/MacOS/$APP"
PL="$DESTINO/Contents/Info.plist"
$PB -c "Set :CFBundleExecutable $APP" "$PL"
$PB -c "Set :CFBundleName $APP" "$PL"
$PB -c "Delete :CFBundleDisplayName" "$PL" 2>/dev/null || true
$PB -c "Add :CFBundleDisplayName string $NOME" "$PL"
$PB -c "Set :CFBundleIdentifier $BUNDLE" "$PL"
echo "Info.plist:"; plutil -p "$PL" | grep -E 'CFBundle(Executable|Name|DisplayName|Identifier|URLSchemes)|"[a-z-]+"$' || true
# Sem certificado Apple: assinatura ad-hoc (obrigatória para rodar em Apple Silicon).
find "$DESTINO/Contents/Frameworks" -name "*.framework" -maxdepth 1 -exec codesign --force --sign - --timestamp=none {} \;
find "$DESTINO/Contents/Frameworks" -maxdepth 1 -type f -name "*.dylib" -exec codesign --force --sign - --timestamp=none {} \;
for bin in "$DESTINO"/Contents/MacOS/*; do [[ $(basename "$bin") == "$APP" ]] || codesign --force --sign - --timestamp=none "$bin"; done
codesign --force --deep --sign - --timestamp=none "$DESTINO"
codesign --verify --deep --strict --verbose=2 "$DESTINO"
"$DESTINO/Contents/MacOS/$APP" --version || true
CREATE_DMG="$(readlink -f "$(command -v create-dmg)")"
sed -i -e 's/MAXIMUM_UNMOUNTING_ATTEMPTS=3/MAXIMUM_UNMOUNTING_ATTEMPTS=7/' "$CREATE_DMG" || true
DMG="$SAIDA/$APP-$VERSAO-$ARQ.dmg"
create-dmg --volname "$NOME" --icon "$APP.app" 200 190 --hide-extension "$APP.app" \
  --window-size 800 400 --app-drop-link 600 185 "$DMG" "$DESTINO"
rm -rf "$DESTINO"
shasum -a 256 "$DMG"
