# Imagem KIWI do Lyra OS Server

`config.xml` é a descrição canônica da ISO live/instalável headless. A imagem
usa openSUSE Leap 16, sem GNOME e sem os componentes desktop do ecossistema
Lyra: administração por `vega-cli`/`vegad`/`vega-web` e acesso SSH. Veja
`docs/server-edition.md` para a arquitetura completa e `docs/server-release-gate.md`
para o gate de go/no-go.

## Instalador na sessão live

Não há sessão gráfica nem RPM de instalador. O overlay em `root/` fixa:

- autologin de root no console (`tty1`) via drop-in systemd
  (`root/etc/systemd/system/getty@tty1.service.d/override.conf`) — a senha
  de root continua bloqueada em `config.xml`, o autologin do agetty ignora
  PAM do mesmo jeito que o autologin gráfico do desktop ignora para o
  `liveuser`;
- `root/root/.bash_profile`, que chama `/usr/sbin/lyra-server-install`
  (instalado a partir de `scripts/server-install.sh`) automaticamente no
  login; `Ctrl+C` ou sair do instalador volta para um shell normal de
  diagnóstico;
- `root/usr/lib/lyra-os/server-release`, metadados de release lidos pelo
  instalador e por evidência de build.

`scripts/server-install.sh` é uma implementação shell independente — não
reaproveita `installer/` (o motor Rust do desktop); reimplementa por conta
própria o subconjunto de particionamento/deploy/bootloader que precisa
(disco único, GPT + ESP, ext4 sem RAID/LVM/Btrfs/Snapper, GRUB com Secure
Boot pela mesma rota do desktop). Veja "Instalador em console" em
`docs/server-edition.md` para o racional completo dessa decisão.

## Build e teste

`kiwi/test/build-and-run-vm.sh` builda a ISO com `kiwi-ng`, valida o
resultado (SquashFS íntegro, `/etc/os-release` e `build-info` batendo com
`release-server.toml`, overlay do instalador de console presente, nenhum home
ou caminho do host incorporado) e sobe uma VM QEMU/KVM descartável. O workdir
padrão é `/var/tmp/lyraos-server-test-$UID`; qualquer
`LYRA_TEST_WORK_DIR` dentro do checkout é recusado antes de ser criado:

```bash
./kiwi/test/build-and-run-vm.sh
```

A porta 2222 do host é encaminhada para a 22 (ssh) da VM, e a 9090 para a
9090 (`vega-web`) — a rede user-mode do QEMU é NAT-only por padrão e o IP da
VM não é alcançável do host sem isso. `--build-only` valida a ISO sem tocar
na VM; `--skip-build` reaproveita a última ISO; `--boot-installed` reinicia
o disco já instalado sem anexar a ISO; `--secure-boot` usa OVMF com chaves
Microsoft. Veja `./kiwi/test/build-and-run-vm.sh --help` para a lista
completa.

Como o `kiwi-ng` nomeia a saída a partir do atributo `<image name="...">` de
`config.xml` (que permanece `lyra-os` — ver comentário em
`image-build-server.toml`), o script renomeia a ISO e os artefatos irmãos
para o nome que `release-server.toml` espera (`lyra-os-server...`) depois do
build.

## Diferenças em relação ao desktop

Sem Btrfs/Snapper/rollback no v1 (ext4 simples), sem tema/ícones Lyra, sem
GNOME, sem `lyra-installer`/`lyra-upgrade`/`lyra-welcome`. Secure Boot está
no escopo do v1, pela mesma rota do desktop (shim assinado do openSUSE).
