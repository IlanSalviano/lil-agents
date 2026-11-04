# lil agents — edição personalizada

Companheiros animados que passeiam pelo Dock do macOS e abrem conversas com
provedores de IA via CLI. Esta distribuição de Ilan Salviano é baseada no projeto
[lil-agents de Ryan Stephen](https://github.com/ryanstephen/lil-agents), sob licença MIT.

**[Baixar a versão mais recente](https://github.com/IlanSalviano/lilagents-releases/releases/latest)** · [Código-fonte da edição](https://github.com/IlanSalviano/lil-agents)

Requer macOS Sonoma 14 ou posterior. Os DMGs são universais (Intel e Apple Silicon),
assinados com Developer ID e notarizados pela Apple. Arraste **lil agents.app** para
**Aplicativos**, ejete o DMG e abra o aplicativo instalado.

Para conversar com IA, instale e autentique o CLI do provedor desejado. Os downloads
não incluem credenciais nem conversas do desenvolvedor. A opção **Sounds** controla
as falas e efeitos. Clique com o botão direito nos personagens para ver seus especiais.

## Atualizações

O menu do lil agents tem **Check for Updates…**. Novas versões e novos personagens
chegam pelo Sparkle, que verifica a assinatura do download antes de instalar.

Este repositório contém os instaladores, notas e feed desta edição. Não é o canal de
atualização do autor original. Se você tem uma versão antiga com o feed original,
instale uma das versões daqui uma vez para passar a receber este canal.

## Vozes por personagem (1.3.2)

Abra **Voices → personagem** na barra ou **Voice** no clique direito. Escolha entre
as vozes instaladas no macOS, agrupadas por idioma e qualidade Standard, Enhanced
ou Premium. **Test Voice** toca uma prévia e **Stop Preview** a interrompe; a escolha
fica salva por personagem. O menu inclui um guia para baixar novas vozes.

As falas sintetizadas de Bill e Amit usam a voz escolhida. Todos os personagens
permitem testar e salvar uma voz; áudios gravados nas animações não são alterados.

## Testar atualizações a partir de uma versão antiga

1. Baixe **[1.3.0, sem Amit](https://github.com/IlanSalviano/lilagents-releases/releases/download/v1.3.0/lil-agents-1.3.0-universal.dmg)**.
2. Encerre o lil agents atual e instale a cópia do DMG em Aplicativos.
3. Abra o app instalado. O menu tem Bruce, Jazz, Zenitsu, Inosuke, Tanjiro, Nezuko e Bill.
4. Selecione **Check for Updates…** e instale a versão mais recente.
5. Após reabrir, Amit aparece com os especiais **Lets Flow!** e **Let's make work flow!**.

A atualização entrega o app completo, incluindo Amit e as opções de voz da versão 1.3.2. Use o instalador 1.3.0 específico para repetir
esse teste; o link de versão mais recente já inclui Amit.

Os personagens inspirados em pessoas reais são interpretações fictícias e não
representações oficiais dessas pessoas ou empresas. As falas usam uma voz do macOS.

## Integridade

Cada release acompanha um arquivo `.dmg.sha256`. O appcast público é publicado
somente depois que o DMG está disponível e seu SHA-256 foi conferido por download.

[Licença MIT](LICENSE) · [Feed de atualizações](https://raw.githubusercontent.com/IlanSalviano/lilagents-releases/main/appcast.xml)
