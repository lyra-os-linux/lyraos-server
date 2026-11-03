# Lyra OS Server 16.1 “Delos”

Versão estável do Lyra OS Server sobre **openSUSE Leap 16.1**, publicada em
**3 de novembro de 2026**: edição sem interface gráfica, com instalador em
console e administração pelo Vega. É a própria ISO da
[RC 3](lyra-os-server-16.1-rc.3.md), a candidata final, promovida por tag sem
rebuild. O arquivo mantém o nome da RC 3, com o mesmo checksum e a mesma
assinatura.

| Campo | Valor |
| --- | --- |
| Versão | `16.1` |
| Tag | `server-v16.1` (o mesmo commit da `server-v16.1-rc.3`) |
| Commit | `9c49dba334c9f935e39d1ae550ddf40170d91c5a` |
| Arquivo | `LyraOS-Server-16.1-rc.3-x86_64.iso` |
| SHA-256 | `1bcb55a7842487ee463bf40640b882f34dd00e1a9a1a31d539a8de39919b7a45` |
| Download | [releases/16.1/stable/server/](https://sourceforge.net/projects/lyra/files/releases/16.1/stable/server/) no SourceForge |
| Publicação da RC 3 | 30/10/2026 |

Quem instalou a RC 3 já tem o sistema da versão estável e só precisa seguir
atualizando. As atualizações do Leap 16.1 final chegam pelo repositório
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

O bundle publicado inclui a ISO, o inventário RPM, a verificação KIWI, os SBOMs
CycloneDX/SPDX, o checksum e a assinatura destacada. Baixe a ISO, o `.sha256` e
o `.sha256.asc` da mesma pasta e confira:

```sh
sha256sum -c LyraOS-Server-16.1-rc.3-x86_64.iso.sha256
gpg --verify LyraOS-Server-16.1-rc.3-x86_64.iso.sha256.asc LyraOS-Server-16.1-rc.3-x86_64.iso.sha256
```

A assinatura deve ser válida para a chave oficial de release
(`01B6 3EED BE6B 0791 26A0 116E FA73 53A1 31EC EFEB`), a mesma das RCs.
