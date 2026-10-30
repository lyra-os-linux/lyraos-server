# Versionamento do Lyra OS Server

Desde a decisão do mantenedor em 13/10/2026, a versão do Lyra OS segue a versão
do openSUSE Leap usado como base: o Lyra OS Server construído sobre o Leap
`16.1` é o **Lyra OS Server 16.1 — Delos**. O formato é `MAJOR.MINOR[.PATCH]`:
`MAJOR.MINOR` é idêntico ao Leap base e `PATCH` é de uso exclusivo do Lyra
(correção, manutenção ou respin da mesma release). Delos é o codename de toda a
geração Server 16.x; a geração Desktop 16.x usa Odisseia.

Até 18/10/2026 o Server era numerado `1.1`, com versionamento independente do
Leap. A Beta 1.1 (`1.1-beta.1.1`, tag `server-v1.1-beta.1.1`) foi publicada com
esse esquema e permanece como registro histórico. Nenhum artefato `1.1-rc.1`
foi assinado ou publicado: a candidata em RC foi renumerada para `16.1-rc.1`.

O Server conserva ciclo de qualificação e namespace de tags independentes do
Desktop, mas não recebe codename diferente. Uma candidata Beta 1 usa
`16.1-beta.1`; uma revisão que permanece dentro desse estágio acrescenta outro
componente, como `16.1-beta.1.1`, com tag `server-v16.1-beta.1.1`. Isso não
equivale a `16.1-beta.2`: a Beta 2 só começa depois que seus próprios
requisitos de promoção forem atendidos.

`release-server.toml` é a fonte canônica para versão, estágio, iteração,
revisão da candidata, codename, base, nome da imagem e arquitetura. O gerador
`scripts/server-release.py` mantém o KIWI e
`/usr/lib/lyra-os/server-release` sincronizados; `LYRA_BASE_VERSION_ID`
conserva a versão do Leap base, que coincide com `MAJOR.MINOR` do Lyra.

A candidata atual é a RC 3, `16.1-rc.3`, tag `server-v16.1-rc.3`, arquivo
`LyraOS-Server-16.1-rc.3-x86_64.iso`. Por decisão do mantenedor em 14/10/2026 o
Server saiu da Beta 1.1 diretamente para a RC 1 (`16.1-rc.1`), construída e
submetida ao gate em VM em 19/10/2026, mas não publicada: o gate encontrou
defeitos nos componentes Vega fora da sessão local, corrigidos na RC 2
(`16.1-rc.2`), publicada em 22/10/2026.

Cronograma decidido pelo mantenedor em 30/10/2026:

- RC 3 (`16.1-rc.3`): publicada antes do previsto (entre 30/10 e 01/11/2026);
  é a candidata final e fica congelada;
- estável `16.1`: 19/11/2026, a mesma ISO da RC 3 promovida por tag
  (`server-v16.1`) e republicação dos artefatos, sem novo build. As
  atualizações do Leap 16.1 GA chegam pelo repositório `update` depois da
  instalação. O nome `LyraOS-Server-16.1-x86_64.iso` só é usado se a promoção
  final exigir uma imagem nova.

Cada RC do ciclo 16.1 é produzida por `scripts/build-server-rc.sh` e publicada
por `scripts/upload-server-rc-sourceforge.sh`; ambos leem o número da candidata
de `release-server.toml` (`stage = "rc"`, `iteration = N`) e publicam em
`releases/16.1/rcN/server/`. Um defeito não trivial no gate gera a próxima RC,
nunca uma redução dos critérios.

Versões calendário e versões `1.x` já publicadas permanecem históricas e podem
ser aceitas como origens legadas explícitas, mas não são produzidas por novos
builds.

Uma release só é promovida com o gate de qualidade verde. Datas são metas de
planejamento ou identificadores de build, não componentes da versão. O suporte
do Leap, o suporte do Lyra Server e o ciclo da geração 16.x são políticas
distintas; nenhuma data de EOL deve ser prometida sem política formal.

O Lyra OS Server 16.1 terá suporte comunitário, sem prazo contratual ou EOL
prometido. O lançamento da versão estável está previsto para **19 de novembro
de 2026**, sempre condicionado ao gate completo. Artefatos legados serão
preservados e republicados com nomes semânticos, mantendo checksums,
assinaturas e proveniência verificáveis.
