# Lyra OS Server

Lyra OS Server é a edição headless do Lyra OS, baseada no mesmo openSUSE Leap
16 do desktop ([`github.com/britors/Lyra`](https://github.com/britors/Lyra)),
sem GNOME e sem os componentes desktop do ecossistema Lyra. Este repositório
contém a descrição KIWI usada para gerar a ISO live e o instalador em console
da edição **Beta 1** para computadores x86_64.

> [!IMPORTANT]
> O projeto ainda está em desenvolvimento. A ISO não deve ser considerada uma
> versão final até que o ciclo completo de build, instalação e inicialização
> do sistema instalado seja validado novamente após as correções mais
> recentes.

## Principais características

- openSUSE Leap 16, sem ambiente gráfico;
- administração via `vega-cli` (linha de comando), `vegad` (daemon) e
  `vega-web` (interface web, porta 9090/tcp), publicados no projeto OBS
  `home:rodrigosbrito:vega`;
- instalador em shell script, interativo, com TUI via `dialog`, rodando no
  console;
- disco único, formatado em ext4 (sem RAID/LVM/Btrfs/Snapper/rollback no v1);
- inicialização UEFI e suporte ao Secure Boot com o shim do openSUSE, mesma
  rota do desktop;
- rede via DHCP automático no v1;
- firewall padrão: apenas SSH e `vega-web` (9090/tcp) abertos.

A arquitetura completa, as decisões tomadas e o histórico de bugs corrigidos
durante o desenvolvimento estão em
[`docs/server-edition.md`](docs/server-edition.md) — incluindo a decisão de
2026-08-11 de manter esta edição no repositório do desktop, revertida em
2026-08-23 ao criar este repositório.

## Build

A imagem é descrita em [`kiwi/config.xml`](kiwi/config.xml) e construída com
KIWI, pelo mesmo mecanismo do repositório desktop:

```bash
python3 scripts/image-build.py validate
python3 scripts/image-build.py export <destino>
```

`scripts/server-release.py` renderiza a versão a partir de
`release-server.toml` — veja
[`docs/release-versioning.md`](docs/release-versioning.md) para o
versionamento completo e o ciclo de release (independente do desktop, mesmos
critérios de estágio: Alpha, Beta, RC, Estável).

## Testes

```bash
python3 -m pytest tests/ -v
```

## Repositório desktop

A contraparte gráfica desta edição, com GNOME, Vega (GTK4), instalador nativo
Rust/Tauri e Btrfs/Snapper, vive em
[`github.com/britors/Lyra`](https://github.com/britors/Lyra).
