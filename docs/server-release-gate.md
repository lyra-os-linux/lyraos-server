# Gate de release — Lyra OS Server alpha1

Este checklist é o contrato de go/no-go da edição server, análogo a
`docs/release-gate.md` (edição desktop) mas recortado para o que realmente se
aplica ao server: sem Lyra Installer gráfico, sem Btrfs/Snapper/rollback (v1
usa ext4 simples, ver `docs/server-edition.md`), sem sessão GNOME. Um
coordenador de release só pode declarar **GO** quando todo item bloqueante
abaixo tiver passado e sua evidência estiver no manifesto final. Evidência
ausente é falha, não uma exceção implícita.

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

Nenhum P0 ou P1 pode ficar aberto na publicação. Um P2 só é aceito quando o
registro de decisão nomeia issue, workaround, responsável e risco residual —
sendo alpha1, é esperado ter arestas (P2/P3), mas não P0/P1.

## Identidade do candidato

- [ ] árvore de código limpa e commit completo registrado;
- [ ] `release-server.toml`, metadados do KIWI (profile `server`), nome do ISO
  e `VERSION_ID` instalado concordam;
- [ ] o inventário de pacotes do ISO contém revisões exatas do OBS
  (`home:rodrigosbrito:lyra`, `home:rodrigosbrito:vega` — sem `fina` nem
  `Virtualization:Appliances:Builder`, que são desktop-only);
- [ ] o candidato só é marcado com tag depois que todos os checks bloqueantes
  passam.

## Evidência exigida

Cada arquivo é JSON estruturado com schema 1 e `"status": "passed"` no
nível raiz. `scripts/image-build.py artifact-manifest --manifest
image-build-server.toml --release-file release-server.toml` também confere
modo esperado, checks não vazios passando, conteúdo do projeto OBS e
cobertura de hardware; um status verde isolado é rejeitado. Diferente do
desktop, **não há item `rollback`** — `image-build-server.toml` já reflete
isso em `required_test_results`:

- [ ] `obs-repositories`: projetos de release publicados; proveniência,
  metadados de repositório, chaves e assinaturas RPM verificados por
  `obs-release.py health` (mesmos projetos OBS do desktop — não existe
  projeto OBS separado para o server);
- [ ] `live-session`: boot da imagem em console (sem sessão gráfica),
  autologin em tty1, ausência de falhas críticas no journal antes do
  instalador rodar;
- [ ] `installer`: `lyra-server-install` completa via `dialog` (partição,
  cópia, chroot, grub) sem cair para um fallback manual;
- [ ] `first-boot`: `kiwi/root/usr/bin/lyra-system-smoke first-boot
  --profile server` — disco instalado boota, root em ext4, conta criada
  funciona, `sshd`/`vegad`/`vega-web`/`firewalld`/`NetworkManager` ativos,
  nenhum artefato live remanescente;
- [ ] `uefi-secure-boot`: cenários suportados de UEFI e Secure Boot passam
  (`lyra-system-smoke secure-boot` — mesmo check do desktop, não é
  profile-específico);
- [ ] `hardware-matrix`: cenários reais/virtuais obrigatórios registrados —
  ver `docs/hardware-matrix.md` e a limitação de mantenedor solo com uma
  única máquina física (mesma restrição do desktop; cobertura primária via
  VM/QEMU é aceita como risco documentado).

## Chave de assinatura do release

Mesma chave do desktop — não há uma chave separada por edição. Ver
`docs/release-gate.md` (seção "Release signing key") para a fingerprint e o
UID atuais; importar `docs/release-signing-key.asc` antes de confiar em
`*.iso.sha256.asc`.

## Checks de artefato e publicação

- [ ] ISO, inventário de pacotes, relatório/verificação do KIWI e ambos os
  formatos de SBOM presentes (mesma lista de `[artifacts] required` de
  `image-build-server.toml`);
- [ ] SHA-256 gerado, assinado com a chave acima e verificado de forma
  independente;
- [ ] notas de release listam requisitos, limitações, issues P2/P3 aceitas e
  workarounds testados — para alpha1, deixar explícito que é uma build
  inicial com arestas esperadas;
- [ ] manifesto de evidência gerado a partir de um commit limpo e contém
  todos os resultados verdes exigidos;
- [ ] ISO e evidência sobem para o SourceForge e são baixados de novo para
  verificação de checksum/assinatura;
- [ ] issue de tracking registra coordenador, horário da decisão, URLs de
  evidência, riscos P2/P3 aceitos e o commit de origem exato.

## Registro de decisão

Mesmo formato de `docs/release-gate.md`, adaptado ao produto:

```text
Decisão: GO | NO-GO
Commit candidato:
Nome do ISO:
SHA-256:
Coordenador:
Horário da decisão (UTC):
Manifesto de evidência:
Issues P2/P3 aceitas e workarounds:
Riscos residuais:
```

## Estado atual (alpha1)

**NO-GO** — nenhum candidato ISO real foi construído e assinado ainda pelo
pipeline completo. Confirmado até aqui: instalação de ponta a ponta em VM
(boot do live → wizard → particiona → copia → chroot → reboot → login →
`vegad`/`vega-web` ativos e respondendo em `http://localhost:9090`, ver
`docs/server-edition.md`). Ainda faltam, nesta ordem: rodar
`scripts/server-release.py check`, `scripts/image-build.py validate/export
--profile server --release-file release-server.toml --manifest
image-build-server.toml`, um build real via `kiwi-ng`
(`kiwi/test/build-and-run-vm.sh --profile server`), `lyra-system-smoke
first-boot --profile server` num disco instalado de verdade (não só a VM de
desenvolvimento), `obs-release.py health`, e só então
`release-artifacts.py generate --release-file release-server.toml --product
"Lyra OS Server"` + `image-build.py artifact-manifest`. Teste em hardware
físico real ainda não aconteceu (só VM até agora) — ver
`[[hardware_matrix_single_machine_risk]]`.

## Referências

- `docs/release-gate.md` — formato original (edição desktop), do qual este
  documento deriva.
- `docs/server-edition.md` — arquitetura da edição server e a seção "Gate e
  evidência" que motivou este documento.
- `docs/hardware-matrix.md` — formato de cobertura de hardware reaproveitado.
- `image-build-server.toml`, `release-server.toml` — manifestos que este gate
  valida.
