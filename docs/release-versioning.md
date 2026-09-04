# Versionamento do Lyra OS Server

O Server segue a política do produto: **Lyra OS Server 1 — Delos**, com versão
própria no formato `MAJOR.MINOR` (com `PATCH` quando necessário) e base tecnológica registrada
separadamente. A versão estável planejada é **Lyra OS Server 1.1 —
Delos**, baseada no **openSUSE Leap 16.1**. Delos é o codename de toda a
geração Server 1.x; a geração Desktop 1.x usa Odisseia.

O Server conserva ciclo de qualificação e namespace de tags independentes do
Desktop, mas não recebe codename diferente. Uma candidata Beta 1 usa
`1.1-beta.1`; uma revisão que permanece dentro desse estágio acrescenta outro
componente, como `1.1-beta.1.1`. A tag correspondente é
`server-v1.1-beta.1.1`. Isso não equivale a `1.1-beta.2`: a Beta 2 só começa
depois que seus próprios requisitos de promoção forem atendidos.

`release-server.toml` é a fonte canônica para versão, estágio, iteração,
revisão da candidata, codename, base, nome da imagem e arquitetura. O gerador
`scripts/server-release.py` mantém o KIWI e
`/usr/lib/lyra-os/server-release` sincronizados.

Esta candidata usa `LyraOS-Server-1.1-beta.1.1-x86_64.iso`; a release estável
usará `LyraOS-Server-1.1-x86_64.iso`.

Versões calendário já publicadas permanecem históricas e podem ser aceitas
como origens legadas explícitas, mas não são produzidas por novos builds.

Uma release só é promovida com o gate de qualidade verde. Datas são metas de
planejamento ou identificadores de build, não componentes da versão. O suporte
do Leap, o suporte do Lyra Server e o ciclo da geração 1.x são políticas
distintas; nenhuma data de EOL deve ser prometida sem política formal.

O Lyra OS Server 1.1 terá suporte comunitário, sem prazo contratual ou EOL prometido.
O lançamento está previsto para **20 de fevereiro de 2027**, sempre condicionado
ao gate completo. Artefatos legados serão preservados e republicados com nomes
semânticos, mantendo checksums, assinaturas e proveniência verificáveis.
