# Capsula TI Remote — clientes Windows e macOS

Compila duas edições do RustDesk com a identidade Capsula TI, já apontadas para o servidor da Capsula TI:

| Edição | Nome no sistema | Para quem | Conexões |
|---|---|---|---|
| **Capsula TI Suporte** | `CapsulaTI-Suporte` | Computadores dos clientes | Só **recebe** (mostra ID e senha) |
| **Capsula TI Remote** | `CapsulaTI-Remote` | Equipe técnica | Só **inicia** conexões |

Saem do GitHub Actions:
- **Windows x64:** `.exe` (abre o app e oferece Instalar) e `.msi` (implantação em massa, GPO e Intune).
- **macOS:** `.dmg` para Apple Silicon (`aarch64`) e Intel (`x86_64`).

Base: RustDesk **1.5.3**, compilado com os mesmos passos do workflow oficial.

## O que a marca altera

- **Configuração embutida no binário:** nome do app, tipo de conexão, servidor e chave.
  - O cliente não lê `custom.txt` externo, então ninguém troca o servidor colocando um arquivo ao lado do executável.
  - Na interface, as telas de servidor, proxy e websocket ficam ocultas.
- **Servidor e chave padrão** do código trocados pelos da Capsula TI.
- **Ícones e logotipos:** ícone Capsula no app, na barra de tarefas e na bandeja/menu do macOS, e logotipo claro/escuro na tela principal.
- **Metadados:**
  - Windows: nome do produto, empresa, descrição e direitos autorais.
  - macOS: nome do app, bundle id e esquema de link `capsulati-remote://` e `capsulati-suporte://`.
- Sem verificação de atualização da RustDesk. Clientes personalizados não baixam o RustDesk oficial por cima.

Tudo isso fica em `scripts/aplicar_marca.py`. Cada alteração confere o texto original do RustDesk e **para a compilação com erro claro** se algo mudou numa versão nova.

## Passo a passo (primeira vez)

1. **Crie a conta no GitHub** em https://github.com/signup. Pode ser com o e-mail da Capsula TI.
2. **Crie o repositório:** botão **New repository**.
   - Nome: `capsulati-remote-clientes`.
   - Visibilidade **Public**. É recomendado por dois motivos:
     - repositório público tem minutos ilimitados de GitHub Actions, inclusive macOS (no privado o macOS consome 10× e o plano grátis aguenta poucos builds por mês);
     - cumpre a licença AGPL-3.0, porque o código das alterações fica disponível para quem recebe o app.
3. **Envie os arquivos:** extraia este pacote e, no repositório, use **Add file > Upload files**.
   - Arraste **todo o conteúdo** da pasta, incluindo a pasta `.github`.
   - No Windows, se a pasta `.github` não aparecer, ative "Itens ocultos" no Explorador.
4. **Cadastre o servidor:** **Settings > Secrets and variables > Actions > aba Variables > New repository variable**.
   - `RUSTDESK_HOST`: nome ou IP público do servidor hbbs/hbbr, o mesmo que aparece em Downloads no painel.
   - `RUSTDESK_KEY`: saída de `sudo cat /opt/capsulati-remote/data/id_ed25519.pub`.
5. **Libere o Actions:** **Settings > Actions > General**.
   - Marque "Allow all actions and reusable workflows".
   - Em *Workflow permissions*, marque "Read and write permissions".
6. **Compile:** aba **Actions > Compilar clientes Capsula TI > Run workflow**. Escolha edição e plataforma, ou deixe "ambas".
   - O primeiro build leva de 60 a 90 minutos. Os seguintes são mais rápidos por causa do cache.
   - A primeira etapa ("Validar configuração e marca") roda em 2 a 3 minutos e já acusa servidor/chave errados ou incompatibilidade com o código do RustDesk.
7. **Baixe os instaladores:** em **Releases** (lateral direita do repositório) ou na página da execução, em *Artifacts*.

> Dica: com o GitHub conectado ao Claude (claude.ai > Configurações > Conectores > GitHub), eu consigo enviar alterações, disparar os builds e corrigir falhas diretamente.

## Instalação

### Windows
- Execute o `.exe`. Sem assinatura de código, o SmartScreen avisa: clique em **Mais informações > Executar assim mesmo**. O app abre e oferece **Instalar**.
- Em massa: `msiexec /i CapsulaTI-Suporte-1.5.3-x86_64.msi /qn`.
- Acesso não assistido (computador do cliente): depois de instalar, defina uma senha permanente pela tela **Segurança** do app ou, como administrador:
  `"C:\Program Files\CapsulaTI-Suporte\CapsulaTI-Suporte.exe" --password SenhaForteAqui`
- Veja o ID do computador com `--get-id` e cadastre-o no painel.

### macOS
1. Abra o `.dmg` e arraste o app para **Aplicativos**.
2. Na primeira abertura o macOS bloqueia o app, porque ele não tem assinatura Apple. Vá em **Ajustes do Sistema > Privacidade e Segurança** e clique em **Abrir mesmo assim**.
3. Conceda **Gravação de Tela** e **Acessibilidade** quando solicitado. Sem essas permissões, o técnico vê a tela preta ou não controla o mouse.
4. A cada atualização do app, o macOS pode pedir as permissões de novo. Isso acontece enquanto não houver assinatura Apple.

## Integração com o painel Capsula TI Remote

- O botão **Conectar** do painel (Build0003) abre links `rustdesk://`. Com a edição Técnico, o link passa a ser `capsulati-remote://connection/new/<ID>`, e isso exige um ajuste no painel.
- Publique os instaladores na página Downloads do painel com:
  `sudo /opt/capsulati-remote/panel/gerenciar-painel.sh publicar-download ARQUIVO NOME VERSAO`

## Atualizar para uma nova versão do RustDesk

1. Troque `RUSTDESK_TAG`/`VERSION` em `.github/workflows/compilar-clientes.yml`.
2. Confira as versões de Flutter, Rust e vcpkg no `flutter-build.yml` oficial da nova tag.
3. Rode o workflow. Se o RustDesk tiver mudado um dos trechos alterados, a etapa "Validar configuração e marca" para e indica o arquivo.

## Assinatura de código (quando houver)

- **Windows:** com um certificado de assinatura de código (OV/EV ou Azure Trusted Signing), adicionamos a etapa de assinatura dos `.exe`/`.msi` e o aviso do SmartScreen some.
- **macOS:** com a conta Apple Developer (US$ 99/ano), o app passa a ser assinado com Developer ID e notarizado. Assim abre sem bloqueio e as permissões não se perdem nas atualizações.

## Licença

O RustDesk é licenciado sob a **AGPL-3.0** (arquivo `LICENSE`). Os binários gerados são obra derivada. O "código-fonte correspondente" é o RustDesk na tag indicada, mais as alterações aplicadas por `scripts/aplicar_marca.py`, ambos públicos neste repositório. Mantenha o repositório acessível a quem receber os instaladores.

As marcas "RustDesk" pertencem aos seus titulares. A identidade Capsula TI pertence à Capsula TI.
