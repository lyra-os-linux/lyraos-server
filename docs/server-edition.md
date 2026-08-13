# Lyra OS Server

Este documento é a arquitetura da edição **server** do Lyra OS: uma imagem
headless, baseada na mesma base openSUSE Leap 16.0, sem GNOME e sem os
componentes de desktop do ecossistema Lyra, com `vegad` + `vega-cli` +
`vega-web` como interface de administração.

Decisões tomadas em conversa (2026-08-11):

- mesmo repositório Lyra, não um repositório novo;
- imagem headless: sem GNOME, sem tema Lyra, sem ícones, sem a extensão
  Sheliak, sem Chord (terminal), sem Beam nem Sulafat (clientes de acesso
  remoto), sem Fina;
- pacotes Lyra incluídos: `vegad` (daemon) + `vega-cli` + `vega-web`, todos
  publicados em `home:rodrigosbrito:vega` (`vega-web` já existe — corrigindo
  premissa anterior deste rascunho, que assumia que ainda precisava ser
  desenvolvido);
- instalador em **shell script** independente, rodando em console, de forma
  **interativa** — TUI via `dialog` (2026-08-11, decisão tomada durante o
  primeiro teste em VM; a versão inicial usava só `read -p`), não
  desatendido/autoyast;
- armazenamento do instalador v1: **disco único, sem RAID/LVM**, formatado em
  **ext4** (sem Btrfs, sem Snapper/rollback — coerente com não ter
  Snapper/rollback no v1);
- **Secure Boot entra no v1**, mesma rota do desktop (shim assinado do
  openSUSE) — não é um trade-off aceito nem fica para v2;
- **rede via DHCP automático no v1**, sem prompt de IP estático no
  instalador — configuração de IP estático fica para depois da instalação,
  via `vega-cli`/`vega-web`, se necessário;
- **firewall padrão: só SSH e `vega-web` (porta 9090/tcp) abertos**, mais
  nenhuma porta;
- **nome da edição: "Lyra OS Server"; codinome do ciclo 1.0: "Delos"** — o
  codinome é identidade humana do produto e não altera nome de pacote, volume,
  tag ou o schema mecânico de `release-server.toml`; o ciclo Server 1.1 usa
  o codinome **"Tebas"** sob a mesma regra;
- **ciclo de release próprio**, não compartilha `release.toml`/calendar
  version com a ISO desktop, mas segue o mesmo esquema alpha/beta/rc/final
  já usado pelo desktop (`docs/release-versioning.md`) — começa em alpha1;
- **RAID/LVM/Snapper/Btrfs ficam fora de escopo sem critério de entrada
  definido** — não é "quando X acontecer, entra"; fica simplesmente para
  quando o Rodrigo decidir revisitar, sem gatilho pré-combinado.

## Escopo

A ISO desktop já decide o conjunto GNOME + Vega (GTK4) + Sheliak + Fina +
Beam/Sulafat como experiência padrão (`kiwi/config.xml`,
`PROMPT-LYRA-OS.md`). A edição server inverte isso: mesma base (Leap 16.0,
kernel-default, repositórios oficiais + OBS do Lyra, mesma política de
assinatura), mas sem ambiente gráfico e sem os componentes de desktop —
administração por console e por `vega-web`. O sistema de arquivos instalado
diverge também: o desktop usa Btrfs+Snapper, o server v1 usa ext4 simples
(sem rollback).

Fora de escopo até decisão em contrário:

- RAID, LVM, Btrfs e Snapper/rollback no instalador do server — sem critério
  de entrada definido para um v2, fica pra quando o Rodrigo decidir
  revisitar (Secure Boot, diferente desses, já está dentro do escopo do v1);
- qualquer pacote de desktop (GNOME, Firefox, CUPS, Flatpak, tema, ícones);
- instalação desatendida/arquivo de resposta (autoyast-like) — o v1 é
  interativo;
- arquitetura ARM64, mesma exclusão da ISO desktop.

## O que muda em relação à ISO desktop

| Item | ISO desktop | Edição server |
|---|---|---|
| Ambiente gráfico | GNOME 48+, Wayland | ausente (headless) |
| Tema/ícones Lyra | `lyra-os-theme`, ícones custom | ausentes |
| Beam, Sulafat | pré-instalados, favoritos GNOME | ausentes |
| Chord | não pré-instalado | ausente |
| Sheliak (dock GNOME) | pré-instalado + schema override | ausente |
| Fina | pré-instalado | ausente |
| Vega | `vega-gtk` (frontend GTK4) | `vega-cli` + `vegad` + `vega-web` |
| Instalador | Lyra Installer nativo (Rust/Tauri, GUI WebKitGTK) | script shell em console, interativo |
| Storage do instalador | disco único, RAID novo/existente, LVM, Btrfs+Snapper+rollback | v1: disco único, ext4, sem RAID/LVM/rollback |
| Perfil/target KIWI | único (`config.xml` sem `<profiles>`) | segundo profile reaproveitando a base |
| Nome/volid da imagem | `lyra-os` "Odisseia" / `LYRA_OS_...` | "Lyra OS Server 1.0 Delos" na comunicação; nome técnico e volid permanecem sem codinome; ciclo alpha/beta/rc/final próprio, começando em alpha1 |

## Mecânica de build (KIWI)

O `kiwi/config.xml` usa hoje os profiles nativos `desktop` e `server`, com
uma base comum (repositórios oficiais + OBS do Lyra, kernel-default e branding
neutro). O profile `server`:

- remove os pacotes de desktop listados acima (`beam`, `sulafat`,
  `sheliak`, `fina`, `vega-gtk`, o grupo GNOME, `lyra-os-theme` e os ícones);
- adiciona `vega-cli` e `vegad` explicitamente (hoje eles só chegam de forma
  transitiva via dependências do `vega-gtk` — comentário em
  `kiwi/config.xml:334-338` — o profile server precisa declará-los
  diretamente, já que `vega-gtk` não entra);
- adiciona `vega-web`, publicado no mesmo projeto OBS `home:rodrigosbrito:vega`
  de `vega-gtk`/`vega-cli`/`vegad` — mesmo repositório `repo-vega` já
  declarado em `kiwi/config.xml`, sem repositório novo a adicionar;
- ajusta `name`/`displayname`/`volid`/`bootloader-theme`/`bootsplash-theme`
  para algo neutro (sem a identidade visual Lyra Enterprise usada no
  desktop, que depende do tema removido);
- troca o instalador do live: hoje a imagem instala o RPM do Lyra Installer
  gráfico e o abre via GDM autostart (`kiwi/README.md`); o profile server não
  tem sessão gráfica nenhuma, então precisa de outro mecanismo de start do
  instalador em console (ver seção seguinte).

**Implementado parcialmente**: `scripts/image-build.py`'s `export()` agora
lê os profiles de `kiwi/config.xml` e copia o overlay de cada um que
existir em disco (`kiwi/<profile>/`) — sem isso, `kiwi/server/` (autologin,
instalador pinado, metadados de release) ficaria de fora do export
canônico e o build do profile server falharia logo no `config.sh` por
falta de `/usr/lib/lyra-os/server-release`. Isso não exigiu hardcodar
"server": qualquer profile novo que ganhar um diretório próprio é pego
automaticamente.

O pipeline de evidência seleciona essa política por
`image-build-server.toml`; o helper de build passa `--profile server` ao
`kiwi-ng`. O CI publicado ainda executa somente o fluxo desktop.

## Instalador em console

Decisão já tomada: **script shell independente**, não um novo frontend sobre
`lyra-installer-core`/`service` (o instalador Rust existente em
`installer/`). Isso foi discutido explicitamente: o instalador desktop já
separa lógica de domínio (`lyra-installer-core`: particionamento GPT/Btrfs,
`PlanBuilder`, deploy do rootfs, GRUB/Secure Boot, Snapper) do frontend
(`src-tauri/`), justamente para permitir frontends alternativos sem duplicar
essa lógica — mas a decisão consciente foi não reaproveitar isso agora, então
o script shell **vai reimplementar por conta própria** o subconjunto v1 do
particionamento e deploy que precisar. Isso é aceito como trade-off, não um
descuido: vale revisitar se o server precisar do mesmo nível de
Btrfs+Snapper+GRUB rollback que o desktop já tem testado.

**Implementado** (2026-08-11) em [`scripts/server-install.sh`](../scripts/server-install.sh)
— mesmo diretório de `image-build.py`/`release.py`, não um diretório novo,
como decidido em conversa. Fluxo real:

1. boot do live: sem GDM, autologin de root no console (`tty1`) via
   drop-in systemd (`kiwi/server/etc/systemd/system/getty@tty1.service.d/`)
   — senha de root continua bloqueada em `kiwi/config.xml`, o autologin do
   agetty ignora PAM do mesmo jeito que o autologin do GDM já ignora para o
   `liveuser` no desktop. `/root/.bash_profile` chama o instalador
   automaticamente; Ctrl+C ou saída do instalador volta para um shell
   normal de diagnóstico;
2. prompts interativos: idioma (pt_BR.UTF-8/en_US.UTF-8), teclado (us/
   br-abnt2), fuso (America/Sao_Paulo/UTC), hostname, disco alvo (menu
   numerado, exclui a própria mídia live automaticamente — qualquer disco
   com alguma partição montada no momento fica de fora da lista), usuário e
   senha (confirmação dupla, nunca em argv, só via stdin do `chpasswd` —
   mesma regra do instalador desktop). Sem prompt de rede: DHCP automático,
   sem pergunta. Conjunto de idioma/teclado/fuso é propositalmente enxuto
   no v1 (2 opções cada) — expandir é trabalho futuro, não bloqueio;
3. particionamento do disco único (GPT + ESP), `wipefs -a` antes do
   `sgdisk --zap-all` (mesma lição do bug real corrigido no instalador
   desktop, commit `9be2782`), formatação em ext4, mount;
4. cópia do sistema via `tar --one-file-system` a partir da própria sessão
   live já montada (squashfs+overlay) — sem precisar localizar/extrair o
   squashfs original à parte;
5. chroot no destino: timezone/locale/teclado/hostname, criação do usuário
   (grupo `wheel`, sudo sem senha para o grupo), habilita
   `NetworkManager`/`firewalld`/`sshd`/`vegad`/`vega-web`, reduz os
   repositórios Lyra/Vega para prioridade 90 no sistema instalado, abre só
   `ssh` e `9090/tcp` no firewalld, gera chaves SSH exclusivas e executa
   `dracut --force --regenerate-all`;
6. bootloader: `grub2-mkconfig` + `shim-install`, com bind mount
   **recursivo** de `/sys` no chroot (`mount --rbind`, não `--bind`) — é a
   mesma causa raiz que o instalador desktop documentou e corrigiu
   (`MountVirtualFs`, `installer/README.md`): um bind simples não propaga
   o `efivarfs` já montado na sessão live, e a instalação "termina com
   sucesso" sem entrada NVRAM real;
7. remove os artefatos exclusivos da sessão live do destino (override do
   getty, `.bash_profile`, o próprio script instalador) — mesma lógica do
   `LIVE_ONLY_ARTIFACTS` do instalador desktop. Esquecer isso deixaria um
   shell de root sem autenticação em todo boot do sistema instalado;
8. reboot no sistema instalado, com `vegad`/`vega-web` habilitados.

O binário shipado na imagem (`kiwi/server/usr/sbin/lyra-server-install`,
overlay por profile do KIWI — só entra quando o profile `server` está
ativo) é uma **cópia pinada** do arquivo fonte acima, igual ao padrão já
usado pelo wrapper/launcher/ícone do Lyra Installer no desktop: um teste
(`tests/test_server_install.py`) garante que as duas cópias continuam
byte-idênticas, para não haver deriva silenciosa entre o que está no
`scripts/` e o que realmente vai pra imagem.

**Status de teste**: `kiwi/test/build-and-run-vm.sh` ganhou suporte a
`--profile server` (2026-08-11) para viabilizar esse teste. Primeira
tentativa real de `kiwi-ng system build --profile=server` encontrou um bug
real: `kiwi/edit_boot_config.sh` exigia incondicionalmente o asset de tema
GRUB do desktop (`/usr/share/grub/themes/Lyra-OS/theme.txt`, do pacote
`lyra-os-theme`), que não existe no profile server — o build falhava antes
de sequer chegar no instalador. Corrigido: o hook agora só configura
`GRUB_THEME` quando o asset existe, em vez de exigi-lo sempre (detecção por
presença do arquivo, não por profile hardcoded, já que esse hook roda fora
do chroot e não tem acesso a `$kiwi_profiles`). Coberto por
`tests/test_image_build.py::test_installed_grub_theme_contract_is_validated_by_build_and_installer`.

Segundo bug real encontrado logo em seguida: `kiwi-ng` sempre nomeia o ISO
de saída a partir de `<image name="...">` no elemento raiz do
`kiwi/config.xml`, que **não pode** ser escopado por profile (diferente de
`<preferences>`/`<packages>`) — o build do server terminava com sucesso mas
produzia `lyra-os.x86_64-2026.08-alpha1.iso` em vez de
`lyra-os-server.x86_64-2026.08-alpha1.iso`. Corrigido em
`kiwi/test/build-and-run-vm.sh`: quando `--profile=server`, renomeia o ISO e
os artefatos irmãos (`.changes`/`.packages`/`.verified`) pro nome esperado
por `release-server.toml` antes de seguir, em vez de tentar forçar o KIWI a
ser profile-aware sobre esse atributo específico.

Terceiro bug real, já dentro da instalação em si (o ISO chegou a bootar e
rodar o instalador): `scripts/server-install.sh` falhava com "choice:
unbound variable" na seleção de disco. Causa: `choose_from_menu()` usava
uma variável local chamada `choice` pro próprio loop de leitura, e
`choose_disk()` a chama como `choose_from_menu choice ...` — passando
literalmente o nome "choice" como variável de saída. Bash resolve nomes
não qualificados pelo escopo `local` mais próximo, então a `choice` interna
de `choose_from_menu` sombreava a de `choose_disk`, e o `printf -v`
escrevia na variável errada. `shellcheck` não pega esse tipo de bug (é
comportamento de escopo em tempo de execução, não sintático). Corrigido
renomeando a variável interna para `__choice` (mesma convenção de
`__out`), e coberto por um teste de comportamento real (não só grep de
texto) em `tests/test_server_install.py`, que reproduz exatamente esse
padrão de chamada.

Nesse mesmo lote, o Rodrigo pediu explicitamente pra trocar os prompts de
`read -p` puro para uma TUI com `dialog` — reescrito por completo
(`dialog_menu`/`dialog_inputbox`/`dialog_passwordbox`/`dialog_yesno`,
mantendo a mesma convenção `__`-prefixada nas variáveis internas por causa
do bug acima). Pacote `dialog` adicionado ao profile server.

Mais dois problemas reais apareceram na mesma rodada de teste, ambos
mostrados no console da VM (print colado pelo Rodrigo):

- `partprobe: command not found` — o binário vem do pacote `parted`, que
  não estava na lista do profile server (confirmado contra o RPM real
  nesta própria máquina de desenvolvimento: `rpm -ql parted | grep
  partprobe`). Adicionado.
- `tar: ./sys: file changed as we read it`, interrompendo a instalação.
  GNU tar retorna código de saída **1** (não 2) pra avisos não-fatais como
  esse — não é incomum ao ler `/sys` (metadados mudam o tempo todo no
  kernel), e `set -e`/`pipefail` tratava isso como erro fatal. Corrigido:
  os dois lados do pipe do `tar` agora só falham de verdade se algum
  retornar código ≥ 2.

A primeira tentativa desse último fix (`set +e` ao redor do pipe, sem mais
nada) **não resolveu** — mesmo sintoma reapareceu num teste seguinte. Causa
real, mais sutil: a `trap ... ERR` registrada no topo do script dispara em
qualquer comando que retorne não-zero **independente do estado de
`errexit`** (só se isenta dentro de condições `if`/`while`/`&&`/`||`/`!`,
não por causa de `set +e`), e `pipefail` — opção separada, que `set +e` não
desliga — continuava fazendo o pipe reportar não-zero. A trap disparava
antes do código de tolerância rodar. Corrigido desabilitando a trap também
(`trap - ERR` antes do `set +e`, restaurada depois). Uma primeira reprodução
isolada via `bash -c '...'` não pegou o bug (erro de aspas mascarou o
resultado); só reproduziu de verdade extraindo o código real do script em
`tests/test_server_install.py::TarExitStatusToleranceTests`, que passa um
`tar` falso pelo PATH e confirma os dois lados: código 1 não aborta, código
2 aborta com a mensagem específica (não a genérica da trap).

Com o `tar` corrigido de verdade, a instalação avançou até o chroot e
achou mais um bug real: `useradd: grupo 'wheel' não existe`. No desktop o
grupo `wheel` já existe de algum jeito não rastreável a nenhum pacote
específico (procurei em todos os scriptlets RPM instalados nesta máquina,
nenhum cria `wheel`) — o profile server, com um conjunto mínimo de
pacotes, não ganha esse grupo de graça. Corrigido criando o grupo
explicitamente (`groupadd -f wheel`) antes do `useradd`, em vez de assumir
que já existe.

Com esse fix, **a instalação completou e o disco instalado deu boot** —
primeiro teste de ponta a ponta real. Apareceram mais dois pontos:

- `sudo` pedia a senha de **root**, não a do usuário criado. Causa: o
  `/usr/etc/sudoers` padrão do Leap vem com `Defaults targetpw` ativo
  ("ask for the password of the target user i.e. root") mais um
  `ALL ALL=(ALL) ALL` que só faz sentido junto com isso — e como root fica
  sem senha utilizável (modelo "root desabilitado"), sudo ficava
  inutilizável pro usuário recém-criado. O instalador desktop (Rust) já
  contorna exatamente isso; replicado aqui: `/etc/sudoers.d/10-server-installer`
  agora começa com `Defaults !targetpw` antes de `%wheel ALL=(ALL) ALL`.
- A pedido do Rodrigo: banner de login mostrando IP/CPU/disco/memória, já
  que não há sessão gráfica pra ver isso de outro jeito. Implementado como
  `kiwi/server/etc/profile.d/lyra-server-info.sh` (overlay estático, chega
  no sistema instalado pela mesma cópia `tar` do resto do `/`, sem precisar
  de lógica no instalador).

Também: como o teste em VM usa `-netdev user` (SLIRP/NAT) do QEMU sem
`hostfwd`, o IP da VM (tipicamente `10.0.2.15`) não era alcançável do host
— dava pra ver mas não pra testar SSH/vega-web de fora. Adicionado
`hostfwd=tcp::2222-:22,hostfwd=tcp::9090-:9090` em
`kiwi/test/build-and-run-vm.sh`, só quando `--profile server`.

**A pedido do Rodrigo**: barra de progresso (`dialog --gauge`) durante a
parte destrutiva da instalação (particiona → formata → copia → configura →
finaliza), em vez de só texto solto rolando na tela. Isso expôs — duas
vezes seguidas, na mesma sessão de trabalho — a mesma classe de bug do
`tar` documentada acima, um nível acima de onde já tinha sido corrigida:

1. O `{ passos da instalação } | dialog --gauge` inteiro precisa do mesmo
   tratamento trap+`set +e` já aplicado ao pipe do `tar`: `pipefail` faz o
   status do pipe inteiro ficar não-zero sempre que o subshell (lado
   esquerdo de qualquer pipe é sempre um subshell em bash) falha, e a trap
   externa disparava antes da checagem de `PIPESTATUS` rodar.
2. Desabilitar a trap/`errexit` externos pra evitar (1) é **herdado pelo
   próprio subshell** (opções e traps são copiadas no fork) — o que
   desligava silenciosamente a detecção de erro de todo comando real lá
   dentro. Um `mkfs`/`chroot`/etc. que falhasse de verdade seria engolido e
   reportado como sucesso. Corrigido fazendo o subshell reativar `set -e` +
   a trap pra si mesmo, logo na primeira linha, independente do estado
   externo.

As duas camadas foram verificadas com reprodução isolada antes de subir
(sucesso e falha, nos dois níveis) e travadas em
`tests/test_server_install.py::GaugePipeErrorDetectionTests`.

Com a instalação rodando de ponta a ponta (via `dialog --gauge`), apareceram
mais dois bugs reais no boot do disco instalado:

- `systemd-vconsole-setup.service` falhava. Causa: `br-abnt2`, oferecido
  como opção de teclado, é um nome de layout **X11/XKB** (variante), não um
  keymap de **console** Linux válido — `loadkeys`/`vconsole.conf` usam uma
  nomenclatura diferente. Confirmado contra esta própria máquina de
  desenvolvimento (uma instalação real do Lyra OS):
  `localectl list-keymaps | grep ^br` só lista `br`, `br-dvorak`,
  `br-nativo(-*)`, `br-nodeadkeys`, `br-thinkpad` — nunca algo com "abnt2".
  `br` sozinho já é o keymap de console real pra um teclado ABNT2 padrão.
  Corrigido trocando a opção `br-abnt2` por `br`.
- `vegad`/`vega-web` pareceram não subir sozinhos num boot anterior
  (contornado manualmente); numa reinstalação seguinte (já com o fix do
  keymap), os dois **subiram sozinhos normalmente** e `vega-web` respondeu
  em `localhost:9090` via `hostfwd` sem intervenção. Causa raiz do episódio
  anterior não identificada com certeza — não investigado mais a fundo já
  que não reproduziu de novo; se voltar a acontecer, os comandos de
  diagnóstico ficam registrados aqui: `systemctl is-enabled vegad vega-web`,
  `journalctl -u vegad -u vega-web`.
- Barra de progresso corrompida visualmente durante a instalação. Causa:
  mensagens do **kernel** (releitura de tabela de partição, eventos de
  mount/udev — as linhas tipo `[ 455.135181][ T1187] vda: vda1` visíveis
  nos prints anteriores) vão direto pro dispositivo de console, por fora de
  qualquer redirecionamento de shell (`>>"$LOG" 2>&1` não intercepta isso).
  Corrigido baixando o nível de log do console (`dmesg -n 1`, só
  KERN_EMERG passa) durante o gauge, restaurando o valor original
  (lido de `/proc/sys/kernel/printk`, não um padrão fixo) logo depois.

**Instalação completa confirmada em VM, incluindo `vegad`/`vega-web` subindo
sozinhos no boot e respondendo em `http://localhost:9090` via o `hostfwd`**
(boot do live → wizard → particiona → copia → chroot → reboot → login →
serviços ativos). A versão com `dialog --gauge` ainda não foi reconfirmada
de ponta a ponta depois do fix de `dmesg -n` (a barra em si funcionava, só
a corrupção visual foi corrigida depois). Ainda não verificados: a sintaxe
exata de `shim-install --config-file=...` (citada de memória a partir da
descrição do instalador desktop, não reverificada aqui contra o `man` da
ferramenta — o boot funcionou, mas isso não prova que os flags usados são
os "certos"/documentados, só que funcionaram neste caso) e teste em
hardware físico real (só VM até agora).

## Gate e evidência

Formalizado em `docs/server-release-gate.md` (checklist go/no-go completo,
mesmo formato P0-P3 de `docs/release-gate.md`, sem os itens que não existem
no server: Lyra Installer gráfico, Btrfs/Snapper/rollback). Resumo:

- boot da imagem, sessão de instalação em console e instalação completam sem
  fallback nem sessão gráfica;
- `vegad`/`vega-web` ativos e `vega-cli` funcional pós-instalação;
- rede via DHCP funcional pós-instalação, sem intervenção manual;
- Secure Boot ligado e funcional (shim assinado, entrada NVRAM real) — é
  requisito do v1, não um comportamento a registrar caso a caso;
- pelo menos um teste real de instalação completa (ver
  `[[hardware_matrix_single_machine_risk]]`/`docs/hardware-matrix.md` sobre a
  limitação de mantenedor solo com uma única máquina física — mesma restrição
  se aplica aqui, provavelmente via VM/QEMU como cobertura primária).

A evidência é coletada pelo mesmo `kiwi/root/usr/bin/lyra-system-smoke`
usado no desktop, agora com uma flag `--profile {desktop,server}`: o modo
`first-boot` compara o filesystem raiz contra `ext4` (não `btrfs`), pula o
check de Snapper, checa a lista de unidades do server
(`sshd`/`vegad`/`vega-web`/`firewalld`/`NetworkManager` em vez de
`gdm`/`cups`/`graphical.target`) e usa uma lista própria de artefatos
"live-only" (autologin do tty1, o instalador pinado). O pipeline de
evidência ponta a ponta (`scripts/image-build.py`, `scripts/
release-artifacts.py`) também ganhou um `--profile`/`--release-file` e um
manifesto próprio, `image-build-server.toml` (sem `fina`/
`Virtualization:Appliances:Builder` nas fontes OBS, sem `rollback` nos
resultados exigidos). `scripts/obs-release.py` não precisou de nenhuma
mudança: ele opera nos projetos OBS de pacote (lyra/vega/fina), que são
compartilhados entre as duas edições — não há projeto OBS separado para o
server.

## Referências

- `PROMPT-LYRA-OS.md` — especificação da ISO desktop atual, base que a
  edição server parte e diverge.
- `kiwi/config.xml` — lista de pacotes Vega/Beam/Sulafat/
  Sheliak/Fina da ISO desktop, ponto de partida para o profile server.
- `docs/image-builds.md:117-118` — mesmo limite já aplicado à ISO NVIDIA:
  deliverable adicional não pode introduzir flavor de imagem na OBS nem
  bloquear a ISO padrão; vale confirmar se essa regra também se aplica à
  edição server.
- `docs/nvidia-iso.md` — precedente direto de rascunho de arquitetura de uma
  variante de imagem, mesma estrutura de documento.
- `installer/README.md` e `docs/installer-architecture.md` — arquitetura do
  instalador desktop (`lyra-installer-core`/`service`/`src-tauri`) que o
  instalador shell do server deliberadamente não reaproveita.
- `docs/release-gate.md`, `docs/hardware-matrix.md` — formato de gate e de
  cobertura de hardware reaproveitados para a evidência da edição server.
