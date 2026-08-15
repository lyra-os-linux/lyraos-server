# Gate de release — Lyra OS Server Beta 1

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
sendo Beta 1, somente P2/P3 documentadas podem ser aceitas; não pode haver
P0/P1 na publicação.

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

Na sessão live Server, antes de iniciar a instalação, gere a evidência de
console, autologin, identidade da imagem, instalador e journal:

```sh
lyra-live-smoke --profile server --output live-session-result.json
```

Depois de reiniciar pelo disco e entrar com o usuário administrativo criado,
gere a evidência do sistema instalado (o `sudo -v` permite apenas as leituras
privilegiadas não interativas usadas pelo coletor):

```sh
sudo -v
lyra-system-smoke first-boot --profile server --output first-boot-result.json
```

Ambos os comandos retornam status diferente de zero e escrevem
`"status": "failed"` se qualquer check obrigatório falhar. Entradas críticas
do journal só podem ser aceitas explicitamente com `--acknowledge-journal`
apontando para a issue ou workaround revisado.

## Chave de assinatura do release

A assinatura destacada é obrigatória nesta Beta 1, conforme a ADR 0005. É
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

## Estado atual (Beta 1)

**NO-GO** — o mantenedor declarou o congelamento funcional da Beta 1. As
correções bloqueantes #89 (senha no chroot) e #93 (identidade da mídia live)
foram implementadas no commit `303a3b0`; a regressão automatizada, o
`shellcheck`, a sincronização dos metadados e a política de assinatura estão
verdes. Isso valida o código-fonte, não a imagem candidata. Ainda faltam, nesta
ordem: exportar uma árvore limpa, executar o build final via `kiwi-ng`, gerar
`obs-release.py health`, repetir live/installer/first-boot e UEFI/Secure Boot,
registrar a matriz de hardware, gerar os artefatos derivados, assinar o
checksum e produzir o manifesto final com `scripts/build-server-beta1.sh`.
Somente depois ocorre a publicação e verificação pós-download por
`scripts/upload-server-beta1-sourceforge.sh --decision-file ARQUIVO.json`.
O arquivo de decisão usa schema 1 e vincula o GO ao candidato exato:

```json
{
  "schema": 1,
  "decision": "GO",
  "source_commit": "COMMIT_SHA_COMPLETO",
  "iso_filename": "lyra-os-server.x86_64-2026.08-beta1.iso",
  "iso_sha256": "SHA256_DA_ISO",
  "evidence_manifest": "lyra-os-server.x86_64-2026.08-beta1.evidence.json",
  "coordinator": "NOME",
  "decided_at_utc": "AAAA-MM-DDTHH:MM:SSZ",
  "accepted_p2_p3": [],
  "residual_risks": []
}
```

O upload falha fechado se esse registro não corresponder ao manifesto ou se
o GitHub ainda tiver uma issue Server P0/P1 aberta. Teste em hardware
físico real permanece como risco residual (a cobertura aceita foi em VM) — ver
`[[hardware_matrix_single_machine_risk]]`.

O ciclo está em Beta 1 e sob congelamento funcional. O cronograma completo
até a Server 1.0 “Delos” e os critérios de saída estão em
[`release-versioning.md`](release-versioning.md#lyra-os-server-10).

## Referências

- `docs/release-gate.md` — formato original (edição desktop), do qual este
  documento deriva.
- `docs/server-edition.md` — arquitetura da edição server e a seção "Gate e
  evidência" que motivou este documento.
- `docs/hardware-matrix.md` — formato de cobertura de hardware reaproveitado.
- `image-build-server.toml`, `release-server.toml` — manifestos que este gate
  valida.
