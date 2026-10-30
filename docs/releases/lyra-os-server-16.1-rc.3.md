# Lyra OS Server 16.1 “Delos” RC 3

Terceira e última candidata de lançamento do Lyra OS Server 16.1 sobre
**openSUSE Leap 16.1**. A identidade técnica é `16.1-rc.3`, tag
`server-v16.1-rc.3`, arquivo `LyraOS-Server-16.1-rc.3-x86_64.iso`, publicada em
`releases/16.1/rc3/server/` no SourceForge.

## Cronograma (decisão do mantenedor em 30/10/2026)

| Marco | Data |
| --- | --- |
| RC 3 (`16.1-rc.3`) | antecipada, entre 30/10 e 01/11/2026 |
| Versão estável `16.1` | **19 de novembro de 2026**, a mesma ISO da RC 3 promovida por tag |

A RC 3 é a candidata final e fica congelada: com o gate completo verde e sem
P0/P1, a mesma ISO vira a versão estável `16.1` (tag `server-v16.1`) sem
rebuild. As atualizações do Leap 16.1 GA chegam pelo repositório `update`
depois da instalação.

## O que muda em relação à RC 2

A imagem, o instalador e os limites funcionais são os da RC 2. Mudam os
pacotes do Vega e a forma de gravar a identidade do sistema:

- **vegad 5.6.2**:
  - diagnóstico de saúde completo: integridade de pacotes, saúde do disco,
    logs, plataforma (com espaço livre e backup atrasado), segurança, tempo de
    boot e rede, com consertos seguros por achado;
  - **verificação semanal** (`vegad-health-check.timer`, ligado na instalação):
    os testes leves rodam em prioridade baixa e só o que é novo vira aviso;
  - **Liberar espaço** (core dumps, journal antigo, cache do zypper, Flatpak sem
    uso, kernels antigos com snapshot, limpeza do Snapper);
  - pelo SSH, membros de `wheel` leem sem senha o resultado da verificação
    semanal, a medição de espaço e o teste de rede, como na sessão local.
- **vega-cli 5.2.0**:
  - ao abrir, o resumo das novidades da verificação semanal que o usuário
    ainda não viu;
  - Hardware e Kernel → **Diagnóstico de saúde**: modo rápido, teste avulso,
    relatório, Corrigir (lista de achados), Já vi os logs e a frequência da
    verificação;
  - Rede e Firewall → **Minha internet não funciona**;
  - Armazenamento → **Liberar espaço**;
  - o pedido de senha do polkit aparece com a tela limpa e 5 minutos para
    digitar.
- **vega-web 5.2.0** (add-web-diagnostics, decisão do mantenedor em
  30/10/2026):
  - Hardware e Kernel → **Diagnóstico de saúde**: modo rápido, teste avulso,
    progresso, relatório com o boot por fase e a rede passo a passo, Corrigir
    por achado, Já vi os logs, verificação periódica e a última verificação
    semanal;
  - Rede e Firewall → **Minha internet não funciona**, com uma senha só;
  - Armazenamento → **Liberar espaço**, com o acompanhamento da limpeza;
  - **Pedir ajuda** a partir do relatório redigido;
  - o estado da verificação periódica no painel inicial.
- **Identidade do sistema:** o `/etc/os-release` do Lyra passa a ser um
  arquivo próprio, como no Desktop. Antes ele era gravado através do link do
  `Leap-release`, o que alterava o `/usr/lib/os-release` do pacote: o
  diagnóstico de pacotes apontava um "programa alterado" e o Corrigir
  reinstalava o `Leap-release`, trazendo de volta a identidade do openSUSE.
  Uma atualização do próprio `Leap-release` ainda pode trocar a identidade e
  fica como issue conhecida (P3,
  [#38](https://github.com/lyra-os-linux/lyraos-server/issues/38)).

Nenhum aplicativo ou mudança de arquitetura foi adicionado à imagem: edição
headless, instalador em console, instalação UEFI em disco inteiro com GPT, ESP
e raiz ext4, conta administrativa com `sudo`, root bloqueado, SSH, firewalld e
Vega. RAID, LVM, Btrfs, Snapper, BIOS legado, instalação desassistida e upgrade
entre releases (#17) continuam fora de escopo.

## Qualificação obrigatória

O gate de `../server-release-gate.md` é repetido integralmente na ISO exata.
O inventário RPM deve conter `vegad` 5.6.2, `vega-cli` 5.2.0 e `vega-web`
5.2.0 dos targets `openSUSE_Leap_16.1`. Além dos itens das RCs anteriores, o
gate verifica pelo SSH o diagnóstico de saúde, o resumo da verificação semanal,
o teste de rede e o Liberar espaço no `vega-cli`, as mesmas funções no
`vega-web` pelo navegador, e que `rpm -V Leap-release` não acusa nada no
sistema instalado. Teste em hardware físico
permanece risco residual declarado.

Esta RC 3 não deve ser publicada enquanto houver P0/P1 aberto. O bundle
publicado inclui a ISO, inventário RPM, verificação KIWI, SBOMs
CycloneDX/SPDX, checksum e assinatura destacada pela chave oficial de release.
O commit, o SHA-256 e a decisão de GO são preenchidos no bundle publicado.
