# Gate de release — Lyra OS Server 1.1 RC 1

Este checklist é o contrato de go/no-go da edição server, análogo a
`docs/release-gate.md` (edição desktop) mas recortado para o que realmente se
aplica ao server: sem Lyra Installer gráfico, sem Btrfs/Snapper/rollback (v1
usa ext4 simples, ver `docs/server-edition.md`), sem sessão GNOME. Um
coordenador de release só pode declarar **GO** quando todo item bloqueante
abaixo tiver passado. A validação é operacional; arquivos JSON formais de
evidência e um registro separado de decisão não são exigidos para publicar.

## Severidade e política de bloqueio

Mesma escala de `docs/release-gate.md`, adaptada aos itens que existem no
server:

- **P0 — parar imediatamente:** perda de dados, exposição de credencial,
  mídia de instalação corrompida, ou uma configuração padrão explorável (ex.:
  firewall abrindo porta além de ssh/9090, senha padrão).
- **P1 — bloqueia o release:** falha ao bootar a imagem live ou o sistema
  instalado; falha do instalador de console (`lyra-server-install`); rede
  DHCP ou `vegad`/`vega-web` não sobem sozinhos pós-instalação; assinaturas de
  repositório/pacote inválidas; pacote obrigatório não publicado; regressão
  sem workaround seguro.
- **P2 — issue conhecida:** funcionalidade opcional degradada com workaround
  testado e documentado. Precisa aparecer nas notas de release.
- **P3 — follow-up:** defeito cosmético ou de baixo impacto que não invalida
  um cenário suportado. Precisa ter issue de acompanhamento quando não
  corrigido.

Nenhum P0 ou P1 pode ficar aberto na publicação. Sendo RC 1, somente P2/P3
documentadas nas notas podem ser aceitas.

## Identidade do candidato

- [ ] árvore de código limpa e commit completo registrado;
- [ ] `release-server.toml`, metadados do KIWI (profile `server`), nome do ISO
  e `VERSION_ID` instalado concordam;
- [ ] o inventário de pacotes do ISO contém revisões exatas do OBS
  (`home:rodrigosbrito:lyra`, `home:rodrigosbrito:vega` — sem `fina` nem
  `Virtualization:Appliances:Builder`, que são desktop-only);
- [ ] o candidato só é marcado com tag depois que todos os checks bloqueantes
  passam.

## Validação recomendada

Os cenários abaixo continuam compondo a qualificação recomendada, mas seus
arquivos JSON não fazem parte do bundle nem bloqueiam mecanicamente o upload.
Diferente do desktop, **não há item `rollback`**:

- [ ] `obs-repositories`: projetos de release publicados; proveniência,
  metadados de repositório, chaves e assinaturas RPM verificados por
  `obs-release.py health` (mesmos projetos OBS do desktop — não existe
  projeto OBS separado para o server);
- [ ] `live-session`: boot da imagem em console (sem sessão gráfica),
  autologin em tty1, ausência de falhas críticas no journal antes do
  instalador rodar;
- [ ] `installer`: `lyra-server-install` completa via `dialog` (partição,
  cópia, chroot, grub) sem cair para um fallback manual;
- [ ] `first-boot`: disco instalado boota, raiz está em ext4, conta criada
  funciona, `sshd`/`vega-web`/`firewalld`/`NetworkManager` estão ativos,
  `vegad` está disponível por ativação D-Bus (`org.lyraos.Vega1`) e nenhum
  artefato live permanece instalado;
- [ ] `uefi-secure-boot`: cenários suportados de UEFI e Secure Boot passam
  (`mokutil --sb-state` confirma o estado esperado dentro do convidado);
- [ ] `hardware-matrix`: cenários reais/virtuais obrigatórios registrados —
  ver `docs/hardware-matrix.md` e a limitação de mantenedor solo com uma
  única máquina física (mesma restrição do desktop; cobertura primária via
  VM/QEMU é aceita como risco documentado).

Esta imagem não distribui os coletores `lyra-live-smoke` ou
`lyra-system-smoke`. Na sessão live Server, antes de iniciar a instalação,
registre a identidade, unidades com falha e erros do boot com as ferramentas
presentes na própria base:

```sh
cat /usr/lib/lyra-os/server-release
systemctl --failed --no-legend
journalctl -b -p err..alert --no-pager
```

Depois de reiniciar pelo disco e entrar com o usuário administrativo criado,
valide o primeiro boot manualmente:

```sh
sudo -v
findmnt -no SOURCE,FSTYPE /
systemctl is-active sshd vega-web firewalld NetworkManager
busctl --system introspect org.lyraos.Vega1 /org/lyraos/Vega1 >/dev/null
sudo firewall-cmd --list-services
sudo journalctl -b -p err..alert --no-pager
```

Cada comando obrigatório deve retornar zero. Entradas críticas do journal só
podem ser aceitas com issue ou workaround revisado e registrado nas notas de
release.

## Chave de assinatura do release

A assinatura destacada é obrigatória nesta RC 1, conforme a ADR 0005. É
usada a mesma chave do desktop — não há uma chave separada por edição. Ver
`docs/release-gate.md` (seção "Release signing key") para a fingerprint e o
UID atuais; importar `docs/release-signing-key.asc` antes de confiar em
`*.iso.sha256.asc`.

## Checks de artefato e publicação

- [ ] ISO, inventário de pacotes, relatório/verificação do KIWI e ambos os
  formatos de SBOM presentes (mesma lista de `[artifacts] required` de
  `image-build-server.toml`);
- [ ] SHA-256 gerado e verificado de forma independente e assinatura
  destacada validada contra a chave de release;
- [ ] notas de release listam requisitos, limitações, issues P2/P3 aceitas e
  workarounds testados;
- [ ] ISO e artefatos sobem para o SourceForge e são baixados de novo para
  verificação de checksum/assinatura;

## Estado atual (Server 1.1 RC 1)

**NO-GO enquanto a nova base não for requalificada** — a evidência anterior em
VM pertence à base Leap 16.0 e não promove automaticamente esta candidata.
`scripts/build-server-rc1.sh` deve gerar a imagem 1.1 RC 1 de árvore limpa,
os SBOMs e o checksum assinado. O uploader valida a assinatura oficial, consulta
o GitHub e falha fechado se houver issue Server P0/P1; depois baixa novamente a
ISO publicada e verifica checksum e assinatura. Teste em hardware físico real
permanece como risco residual; a cobertura aceita pode ser feita em VM, desde
que todos os itens bloqueantes sejam repetidos sobre Leap 16.1.

Por decisão do mantenedor em 14/10/2026, o ciclo sai da Beta 1.1 diretamente
para a RC 1, com publicação até 31/10/2026. Em 18/10/2026 o mantenedor decidiu
que a RC 1 é a candidata final: com o gate completo verde e sem P0/P1, a mesma
ISO é promovida à versão estável `1.1` em 19/11/2026, sem rebuild sobre os
pacotes GA do Leap 16.1 (03/11/2026); as atualizações GA chegam pelo repositório
`update` após a instalação. A RC 1 inicia o congelamento estrito: somente
correções de bugs, travamentos, segurança e performance crítica em pacotes já
distribuídos. Um defeito não trivial no gate interrompe a promoção e gera a
RC 2, que então é a nova candidata final. O acompanhamento está em
[#25](https://github.com/lyra-os-linux/lyraos-server/issues/25).
O cronograma completo e os critérios de saída estão em
[`release-versioning.md`](release-versioning.md).

## Referências

- `docs/release-gate.md` — formato original (edição desktop), do qual este
  documento deriva.
- `docs/server-edition.md` — arquitetura da edição server e a seção "Gate e
  evidência" que motivou este documento.
- `docs/hardware-matrix.md` — formato de cobertura de hardware reaproveitado.
- `image-build-server.toml`, `release-server.toml` — manifestos que este gate
  valida.
