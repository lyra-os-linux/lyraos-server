# Lyra OS Server 1.1 “Delos” RC 1

Candidata de lançamento do Lyra OS Server 1.1 sobre **openSUSE Leap 16.1**.
Por decisão do mantenedor em 14/10/2026, o ciclo do Server sai da Beta 1.1
diretamente para a RC 1, com publicação prevista até **31 de outubro de 2026**
e a versão estável em **5 de novembro de 2026**, dois dias após o GA do Leap
16.1. A RC 1 inicia o congelamento estrito: a partir dela só entram correções
de bugs, travamentos, segurança e performance crítica.

A identidade técnica é `1.1-rc.1`, tag `server-v1.1-rc.1`, arquivo
`LyraOS-Server-1.1-rc.1-x86_64.iso`. Estas notas acompanham a candidata; o
commit, o SHA-256 e a decisão de GO são preenchidos no bundle publicado.

## Escopo desta candidata

- mesma edição e mesmos limites funcionais da Beta 1.1: instalador em console,
  instalação UEFI em disco inteiro com GPT, ESP e raiz ext4, conta
  administrativa com `sudo`, root bloqueado, SSH, firewalld e Vega (`vegad`,
  `vega-cli`, `vega-web`);
- correções mergeadas depois da Beta 1.1 e nunca publicadas numa imagem:
  limpeza do instalador desde a primeira montagem (#20), recuperação offline
  ext4 para o fluxo NVIDIA via Vega (#22) e Packman Essentials com chave de
  assinatura fixada (#23);
- Vega 5.1.36/5.1.47/5.1.24 com a integração NVIDIA 615.71.09 requalificada
  para o kernel 6.12.0-160100.7 do Leap 16.1.

Nenhum aplicativo, recurso ou mudança de arquitetura foi adicionado. RAID,
LVM, Btrfs, Snapper, BIOS legado, instalação desassistida, upgrade entre
releases (#17) e llama.cpp (#21) continuam fora de escopo e ficam para a 16.2.

## Qualificação obrigatória

A evidência de VM registrada até a Beta 1.1 pertence à base Leap 16.0 e não
promove esta candidata. O gate de `../server-release-gate.md` é repetido
integralmente sobre Leap 16.1 na ISO exata: build KIWI de árvore limpa, boot
live, instalação, primeiro boot, atualização, UEFI/Secure Boot, DHCP, SSH,
firewalld, `vegad`, `vega-cli` e `vega-web`. Os RPMs próprios vêm dos targets
`openSUSE_Leap_16.1` e o inventário não pode conter origem Leap 16.0. Teste em
hardware físico permanece risco residual declarado.

Esta RC 1 não deve ser publicada enquanto houver P0/P1 aberto. Um defeito não
trivial encontrado no gate interrompe a promoção e gera a RC 2; os critérios
não são reduzidos para preservar a data. O bundle publicado inclui a ISO,
inventário RPM, verificação KIWI, SBOMs CycloneDX/SPDX, checksum e assinatura
destacada pela chave oficial de release.

## Versão final

A versão estável `1.1` será reconstruída a partir dos pacotes GA do openSUSE
Leap 16.1 (3 de novembro de 2026) e passará por um gate reduzido antes da
publicação em 5 de novembro de 2026.
