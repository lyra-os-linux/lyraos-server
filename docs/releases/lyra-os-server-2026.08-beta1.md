# Lyra OS Server 2026.08 Beta 1

Esta é a primeira versão sob congelamento funcional do Lyra OS Server 1.0
“Delos”. O fluxo suportado permanece instalação UEFI em disco inteiro, com
GPT, ESP e raiz ext4; RAID, LVM, Btrfs, Snapper, BIOS legado e instalação
desassistida continuam fora de escopo.

## Foco da Beta 1

- impedir que senhas sejam interpretadas pelo shell durante o chroot;
- identificar e excluir a mídia live e seus ancestrais físicos, inclusive em
  cenários copy-to-RAM, com falha fechada antes de qualquer `wipefs`;
- repetir live, instalação, primeiro boot, UEFI/Secure Boot, DHCP, SSH,
  firewalld, vegad e vega-web;
- publicar ISO, inventário RPM, verificação KIWI, SBOMs CycloneDX/SPDX,
  checksum assinado e manifesto final de evidências.

Esta Beta não deve ser publicada enquanto houver P0/P1 aberto ou qualquer
evidência obrigatória ausente. Ver `docs/server-release-gate.md`.
