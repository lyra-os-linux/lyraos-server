# Lyra OS Server 16.1 “Delos” RC 2

Segunda candidata de lançamento do Lyra OS Server 16.1 sobre **openSUSE Leap
16.1**. A versão do Lyra OS segue a numeração do Leap base (decisão de
13/10/2026); o codinome Delos identifica a geração Server 16.x. A identidade
técnica é `16.1-rc.2`, tag `server-v16.1-rc.2`, arquivo
`LyraOS-Server-16.1-rc.2-x86_64.iso`, publicada em
`releases/16.1/rc2/server/` no SourceForge.

A RC 1 (`16.1-rc.1`) foi construída e passou pelo gate em VM em 19/10/2026,
mas **não foi publicada nem etiquetada**: a imagem em si estava sólida
(instalação, primeiro boot, UEFI/Secure Boot, rede, SSH, firewalld), porém o
gate encontrou defeitos nos componentes Vega usados fora de uma sessão local,
e a decisão foi corrigi-los e gerar a RC 2 em vez de publicar com ressalvas.

## Cronograma (decisão do mantenedor em 19/10/2026)

| Marco | Data | Base |
| --- | --- | --- |
| RC 2 (`16.1-rc.2`) | outubro de 2026, após o gate em VM | pacotes RC do Leap 16.1 |
| RC 3 (`16.1-rc.3`) | **5 de novembro de 2026** | pacotes GA do Leap 16.1 (GA em 3 de novembro) |
| Versão estável `16.1` | **19 de novembro de 2026** | a mesma ISO da RC 3, promovida por tag |

A RC 3 é a candidata final: com o gate completo verde e sem P0/P1, a mesma
ISO é promovida à versão estável `16.1` (tag `server-v16.1`) sem rebuild. A
RC 2 existe para validar as correções Vega e a imagem sobre a base RC do Leap
antes do GA. O congelamento estrito continua: apenas correções de bugs,
travamentos, segurança e performance crítica em pacotes já distribuídos.

## O que muda em relação à RC 1

- **vegad 5.1.37**: `Firewall.Status` passa a funcionar fora da sessão local
  ([vegad#79](https://github.com/lyra-os-linux/vegad/issues/79)); a edição é
  detectada pelo marcador `/usr/lib/lyra-os/server-release`, então a imagem
  Server deixa de rodar o daemon com perfil desktop e de consultar Flatpak
  ([#31](https://github.com/lyra-os-linux/lyraos-server/issues/31)); nova
  regra polkit `50-vegad-remote-admin.rules` para administradores (`wheel`)
  fora da sessão local: mutações pedem a própria senha (`AUTH_SELF`), leituras
  administrativas de backup, kernel, snapshots e firewall são liberadas e a
  conta de serviço `vega-web` continua sem privilégio.
- **vega-cli 5.1.25**: ações administrativas via SSH orientam o usuário e
  passam pelo `pkttyagent` em vez de falhar antes do pedido de senha
  ([vega-cli#26](https://github.com/lyra-os-linux/vega-cli/issues/26)).
- **vega-web 5.1.25**: toda ação administrativa pede a senha do usuário e é
  executada pelo broker root com a identidade dele
  ([vega-web#17](https://github.com/lyra-os-linux/vega-web/issues/17));
  leituras de kernel/boot, backup, snapshots, journal e firewall são
  desbloqueadas da mesma forma, sem erros brutos do D-Bus
  ([vega-web#18](https://github.com/lyra-os-linux/vega-web/issues/18));
  tela de login e painel redesenhados com o logo do Lyra, nome e endereços da
  máquina, navegação agrupada e tema claro/escuro seguindo o sistema
  ([vega-web#19](https://github.com/lyra-os-linux/vega-web/issues/19),
  #20, #21); o estado do firewall é relido após cada ação.

Nenhum aplicativo, recurso ou mudança de arquitetura foi adicionado à imagem.
A descrição KIWI, o instalador e os limites funcionais são os da RC 1: edição
headless, instalador em console, instalação UEFI em disco inteiro com GPT, ESP
e raiz ext4, conta administrativa com `sudo`, root bloqueado, SSH, firewalld e
Vega (`vegad`, `vega-cli`, `vega-web`). RAID, LVM, Btrfs, Snapper, BIOS legado,
instalação desassistida, upgrade entre releases (#17) e llama.cpp (#21)
continuam fora de escopo e ficam para a 16.2.

## Qualificação obrigatória

O gate de `../server-release-gate.md` é repetido integralmente sobre Leap
16.1 na ISO exata: build KIWI de árvore limpa, boot live, instalação,
primeiro boot, atualização, UEFI/Secure Boot, DHCP, SSH, firewalld, `vegad`,
`vega-cli` e `vega-web`. O inventário RPM deve conter `vegad` 5.1.37,
`vega-cli` 5.1.25 e `vega-web` 5.1.25 dos targets `openSUSE_Leap_16.1`, sem
origem Leap 16.0. Os itens que falharam na RC 1 são verificados explicitamente:
`vega-cli` administrando via SSH com pedido de senha, `vega-web` executando
ações e leituras administrativas após a confirmação de senha, `vegad` em perfil
`server` e `Firewall.Status` respondendo fora da sessão local. Teste em
hardware físico permanece risco residual declarado.

Esta RC 2 não deve ser publicada enquanto houver P0/P1 aberto. Um defeito não
trivial encontrado no gate gera uma nova RC; os critérios não são reduzidos
para preservar a data. O bundle publicado inclui a ISO, inventário RPM,
verificação KIWI, SBOMs CycloneDX/SPDX, checksum e assinatura destacada pela
chave oficial de release. O commit, o SHA-256 e a decisão de GO são
preenchidos no bundle publicado. O acompanhamento está em
[#25](https://github.com/lyra-os-linux/lyraos-server/issues/25).
