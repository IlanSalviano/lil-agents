# Atualizações e releases

Esta edição distribui o app completo pelo Sparkle. Novos personagens chegam
na mesma atualização, sem instalar plugins ou copiar vídeos manualmente.

- Downloads: https://github.com/IlanSalviano/lilagents-releases/releases
- Feed: https://raw.githubusercontent.com/IlanSalviano/lilagents-releases/main/appcast.xml
- Assinatura Apple: Developer ID Application, equipe `22CZXFP6W7`.
- Notarização: perfil `lilagents-notary` no Keychain.
- Assinatura Sparkle: conta `lilagents` no Keychain, com chave própria deste app.
- Chave pública: `SUPublicEDKey` em `LilAgents/Info.plist`.

As credenciais Apple foram configuradas usando a conta de distribuição já usada
no Tagarela. Nenhuma senha ou chave privada deve ir para o repositório, DMG ou chat.
Faça backup seguro da chave Sparkle pelo utilitário `generate_keys` antes de migrar
de máquina. Não gere outra chave para uma atualização comum.

## Teste inicial

1. Baixe o DMG **1.3.0**, sem Amit, na página dessa release.
2. Encerre o lil agents aberto (isso encerra eventuais sessões de IA dentro dele).
3. Arraste o app do DMG para Aplicativos, substituindo a cópia existente.
4. Ejete o DMG e abra o app de Aplicativos. Amit não deve aparecer no menu.
5. No menu do lil agents, selecione **Check for Updates…**.
6. Instale a versão mais recente (**1.3.2**). Após reabrir, Amit deve aparecer junto com os demais.
7. Clique com o botão direito nele e teste **Lets Flow!** e **Let's make work flow!**.

O feed aponta para 1.3.2 (build 9), que adiciona escolha de voz por personagem. Para repetir o teste, reinstale 1.3.0 explicitamente;
baixar “latest” já entrega a versão com Amit. Não é preciso apagar preferências.
Builds antigos da edição original usam outro feed/chave e precisam desta instalação
manual inicial para entrar no canal personalizado.

## Preparar e publicar

Requer Xcode, ffmpeg apenas para preparar personagens, GitHub CLI autenticado,
Developer ID com chave privada e os dois perfis de Keychain descritos acima.

```sh
python3 scripts/release.py prepare --version 1.3.2 --build 9 --notes-file distribution/release-notes/1.3.2.md
python3 scripts/release.py publish --version 1.3.2 --update-feed
```

Para próximas versões, aumente `MARKETING_VERSION` e `CURRENT_PROJECT_VERSION`
no projeto; passe esses mesmos valores a `prepare`. O número de build deve sempre
subir: Sparkle compara `CFBundleVersion`, não apenas a versão comercial.
`--notes-file` fornece as notas exibidas no GitHub e no diálogo do Sparkle.
Sem `--without-amit`, todos os recursos atuais são incluídos. Não reutilize um
número de versão para um binário diferente.

`prepare` compila Release universal (arm64 + x86_64), assina código de dentro para
fora, notariza/staple o app, cria/assina/notariza/staple o DMG, monta e confere seu
conteúdo, valida Gatekeeper e gera o appcast com o utilitário oficial do Sparkle.
Os IDs de submissão Apple são guardados para retomada sem duplicar submissões.

`publish` publica o binário, baixa-o anonimamente e compara SHA-256 **antes** de
atualizar o feed. O repositório público contém apenas distribuição/documentação;
o script não faz push, commit ou tag do checkout de desenvolvimento.

Artefatos ficam em `dist/releases/<versão>/`; logs, app assinado e respostas da
Apple em `build/releases/<versão>/`. `release.json` registra versões, assinaturas,
checksums, arquitetura e IDs de notarização. O comando não substitui o app instalado.

`scripts/package_dmg.py` permanece como empacotador legado sem notarização e com
atualizações desativadas. Para distribuição remota, use `scripts/release.py`.

## Verificação

Além dos checks do pipeline, `scripts/verify_release_cast.swift` verifica a
presença/ausência real dos personagens em um app de teste isolado.
`scripts/verify_remote_update.swift` usa o Sparkle real com o bundle 1.3.0 e o feed
remoto para confirmar que o build 9 é oferecido. Essa checagem não instala nada.
A troca completa via interface fica disponível para o teste manual descrito acima.

Referência: https://sparkle-project.org/documentation/publishing/
