# Lyra OS Server 1.1 “Delos” Beta 1.1

Esta candidata mantém o Lyra OS Server no estágio Beta 1 e migra sua base de
openSUSE Leap 16.0 para **openSUSE Leap 16.1**. Ela não é a Beta 2 e não inclui
as entregas reservadas para esse estágio.

## Escopo desta revisão

- apontar os repositórios oficiais e os projetos OBS do Lyra/Vega para Leap
  16.1;
- reconstruir a imagem e os RPMs consumidos sobre a nova base;
- preservar o mesmo conjunto de recursos, o instalador em console e os limites
  funcionais da Beta 1;
- identificar sem ambiguidade a candidata como `1.1-beta.1.1`, com a tag
  `server-v1.1-beta.1.1`.

Não foram adicionados aplicativos, recursos ou mudanças de arquitetura do
produto. O fluxo suportado continua sendo instalação UEFI em disco inteiro,
com GPT, ESP e raiz ext4. RAID, LVM, Btrfs, Snapper, BIOS legado e instalação
desassistida continuam fora de escopo.

## Impacto, risco e reversão

O benefício é mover a série Server 1.1 para a base Leap 16.1 sem antecipar o
escopo da Beta 2. O impacto alcança kernel, firmware, bootloader, dracut,
bibliotecas do sistema e todos os RPMs próprios consumidos pela imagem. Os
riscos principais são mudanças de dependências e regressões de boot,
instalação, rede ou serviços após o primeiro boot.

A reversão da preparação consiste em restaurar os repositórios e targets Leap
16.0 e voltar à candidata anterior. Não há downgrade automático suportado de
um sistema já instalado sobre Leap 16.1; uma candidata com falha deve ser
retirada antes da publicação.

## Qualificação obrigatória

Por alterar a base inteira, a candidata precisa repetir a resolução e o build
KIWI, boot live, instalação, primeiro boot, atualização, UEFI/Secure Boot,
DHCP, SSH, firewalld, `vegad`, `vega-cli` e `vega-web`. Os RPMs próprios devem
vir dos targets `openSUSE_Leap_16.1` e o inventário não pode conter origem
Leap 16.0.

Esta Beta 1.1 não deve ser publicada enquanto houver P0/P1 aberto. Ver
[`../server-release-gate.md`](../server-release-gate.md). O bundle publicado
deve incluir a ISO, inventário RPM, verificação KIWI, SBOMs CycloneDX/SPDX,
checksum e assinatura destacada.
