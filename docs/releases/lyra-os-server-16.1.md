# Lyra OS Server 16.1 “Delos”

Versão estável do Lyra OS Server sobre **openSUSE Leap 16.1**, publicada em
**3 de novembro de 2026**: edição sem interface gráfica, com instalador em
console e administração pelo Vega. Em 03/11 a ISO da
[RC 3](lyra-os-server-16.1-rc.3.md), a candidata final, foi promovida por tag
sem rebuild, mas ainda se identificava como "16.1 RC 3". Em 14/11/2026 a ISO
estável foi reconstruída com a identidade `16.1`.

| Campo | Valor |
| --- | --- |
| Versão | `16.1` |
| Arquivo | `LyraOS-Server-16.1-x86_64.iso` |
| Build | 14/11/2026; metadados registrados na `main` em `b6658c8` |
| Assinatura | `LyraOS-Server-16.1-x86_64.iso.asc`, chave Lyra OS Release |
| Download | [releases/16.1/stable/server/](https://sourceforge.net/projects/lyra/files/releases/16.1/stable/server/) no SourceForge |
| Tag | `server-v16.1` (o mesmo commit da `server-v16.1-rc.3`, `9c49dba`) |
| ISO da RC 3 | `LyraOS-Server-16.1-rc.3-x86_64.iso`, mantida na mesma pasta; publicada em 30/10/2026 |

Quem instalou a RC 3 tem o mesmo sistema da versão estável e só precisa seguir
atualizando; o `/etc/os-release` dessas instalações continua dizendo "16.1 RC 3". As atualizações do Leap 16.1 final chegam pelo repositório
`update` depois da instalação.

## Suporte

O Lyra OS não é uma rolling release. O Server 16.1 tem **2 anos de suporte**,
até **3 de novembro de 2028**, e recebe as correções pelos repositórios de
pacotes dele. O fonte da release fica na tag `server-v16.1`, e as correções da
16.1 entram pela branch `release/16.1` ([política de releases e suporte](https://github.com/lyra-os-linux/.github/blob/main/SUPPORT.md#ciclo-de-releases-e-suporte)).

O Vega (`vegad`, `vega-cli` e `vega-web`) não pertence a uma release: continua
sendo desenvolvido e chega ao Server 16.1 pelas atualizações.

## O que o Server 16.1 traz

- **Edição headless** sobre o Leap 16.1: instalador em console, instalação UEFI
  em disco inteiro com GPT, ESP e raiz ext4, conta administrativa com `sudo`,
  root bloqueado, SSH e firewalld.
- **Vega no terminal e no navegador** (`vega-cli` e `vega-web`), com
  administração remota pelo SSH:
  - **Diagnóstico de saúde**: integridade de pacotes, saúde do disco, logs,
    plataforma (com espaço livre e backup atrasado), segurança, tempo de boot
    e rede, com consertos seguros por achado;
  - **verificação semanal** (`vegad-health-check.timer`, ligado na
    instalação), com o resumo das novidades ao abrir o `vega-cli`;
  - **Minha internet não funciona**, **Liberar espaço** e **Pedir ajuda**.
- **Identidade própria do sistema:** o `/etc/os-release` do Lyra é um arquivo
  próprio, e o diagnóstico de pacotes não propõe mais reinstalar o
  `Leap-release`.

O detalhe de cada etapa está nas notas da [RC 3](lyra-os-server-16.1-rc.3.md),
da [RC 2](lyra-os-server-16.1-rc.2.md) e da [RC 1](lyra-os-server-16.1-rc.1.md).

## Escopo e limites

RAID, LVM, Btrfs, Snapper, BIOS legado, instalação desassistida e upgrade entre
releases ([#17](https://github.com/lyra-os-linux/lyraos-server/issues/17))
ficam fora de escopo.

## Problemas conhecidos

Não há P0 nem P1 abertos. Fica aceito, com prioridade P3:

- [#38](https://github.com/lyra-os-linux/lyraos-server/issues/38): uma
  atualização do próprio `Leap-release` pode trocar a identidade do sistema
  para openSUSE.

O teste em hardware físico continua como risco residual declarado.

## Integridade

A ISO estável vem com a assinatura destacada da própria ISO. Baixe a ISO e o
`.asc` da mesma pasta e confira:

```sh
gpg --verify LyraOS-Server-16.1-x86_64.iso.asc LyraOS-Server-16.1-x86_64.iso
```

A ISO da RC 3, mantida na pasta, segue com o bundle completo (inventário RPM,
verificação KIWI, SBOMs CycloneDX/SPDX, `.sha256` e `.sha256.asc`):

```sh
sha256sum -c LyraOS-Server-16.1-rc.3-x86_64.iso.sha256
gpg --verify LyraOS-Server-16.1-rc.3-x86_64.iso.sha256.asc LyraOS-Server-16.1-rc.3-x86_64.iso.sha256
```

A assinatura deve ser válida para a chave oficial de release
(`01B6 3EED BE6B 0791 26A0 116E FA73 53A1 31EC EFEB`), a mesma das RCs.
