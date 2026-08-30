# Versionamento do Lyra OS Server

O Server segue a política do produto: **Lyra OS Server 1 — Delos**, com versão
própria no formato `MAJOR.MINOR.PATCH` e base tecnológica registrada
separadamente. A primeira versão estável planejada é **Lyra OS Server 1.0 —
Delos**, baseada no **openSUSE Leap 16.1**. Delos é o codename de toda a
geração Server 1.x; a geração Desktop 1.x usa Odisseia.

O Server conserva ciclo de qualificação e namespace de tags independentes do
Desktop, mas não recebe codename diferente. Uma candidata Beta 1 usa
`1.0-beta.1` e a tag `server-v1.0-beta.1`.

`release-server.toml` é a fonte canônica para versão, estágio, iteração,
codename, base, nome da imagem e arquitetura. O gerador
`scripts/server-release.py` mantém o KIWI e
`/usr/lib/lyra-os/server-release` sincronizados.

As ISOs usam `LyraOS-Server-1.0-beta.1-x86_64.iso` durante o desenvolvimento
e `LyraOS-Server-1.0-x86_64.iso` na release estável.

Versões calendário já publicadas permanecem históricas e podem ser aceitas
como origens legadas explícitas, mas não são produzidas por novos builds.

Uma release só é promovida com o gate de qualidade verde. Datas são metas de
planejamento ou identificadores de build, não componentes da versão. O suporte
do Leap, o suporte do Lyra Server e o ciclo da geração 1.x são políticas
distintas; nenhuma data de EOL deve ser prometida sem política formal.

O Lyra OS 1.0 terá suporte comunitário, sem prazo contratual ou EOL prometido.
O lançamento está previsto para **20 de fevereiro de 2027**, sempre condicionado
ao gate completo. Artefatos legados serão preservados e republicados com nomes
semânticos, mantendo checksums, assinaturas e proveniência verificáveis.
