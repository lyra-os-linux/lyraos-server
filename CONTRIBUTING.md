# Contribuindo com o Lyra OS

Este repositório inclui um bootstrap para preparar uma instalação nova do
Lyra OS ou do openSUSE Leap 16.1 para desenvolvimento do sistema e das
ferramentas do ecossistema.

## Antes de formatar

Confirme que todo trabalho importante foi enviado ao GitHub. `git status` deve
ser conferido em cada repositório; commits, branches e stashes que existem só
na máquina não serão recuperados pelo bootstrap.

Faça backup criptografado apenas do que for necessário:

- chaves SSH e GPG;
- configuração Git;
- fontes ou arquivos ainda não publicados;
- configurações pessoais do Codex em `~/.codex`, sem reutilizar `auth.json`
  em armazenamento não criptografado;
- configuração do OSC em `~/.config/osc`, preferindo autenticar novamente.

Tokens, senhas e sessões do GitHub, OBS e Codex não devem ser colocados no
repositório nem incorporados ao script.

## Bootstrap da estação

Na instalação nova, obtenha um checkout, revise o script e execute como usuário
normal, sem `sudo` antes de `bash`:

```bash
git clone https://github.com/lyra-os-linux/lyraos-desktop.git
cd lyraos-desktop
less scripts/bootstrap-development.sh
./scripts/bootstrap-development.sh --dry-run
./scripts/bootstrap-development.sh
```

O próprio script solicita `sudo` somente para instalar pacotes, configurar
libvirt e habilitar o serviço necessário. Ele é idempotente e pode ser
executado novamente após uma atualização.

Para conferir novamente as ações sem modificar o sistema:

```bash
./scripts/bootstrap-development.sh --dry-run
```

Outras opções podem ser vistas com:

```bash
bash scripts/bootstrap-development.sh --help
```

### O que é instalado

- C e C++: GCC, Clang, Make, CMake, Ninja, Meson, Autotools, GDB, LLDB e
  Valgrind;
- controle de versão: Git, Git LFS e GitHub CLI (`gh`);
- RPM e OBS: `rpmbuild`, rpmlint, spec-cleaner, `osc` e cargo-packaging;
- linguagens: Rust/Cargo do Leap, Rust estável via rustup, Go, Node.js 24,
  npm e Python 3;
- aplicações nativas: GTK4, libadwaita, VTE, WebKitGTK, libsoup, OpenSSL,
  D-Bus, polkit, Secret Service e ferramentas AppStream;
- Lyra OS: KIWI, QEMU/KVM com interface GTK, OVMF normal/Secure Boot,
  libvirt, `xorriso`, `lsinitrd` e utilitários para construir e validar a ISO;
- contêineres e utilitários: Podman, Buildah, ripgrep, fd, fzf, bat, tmux e
  ShellCheck;
- Codex CLI oficial, instalado pelo npm no prefixo de usuário `~/.local`.

## Autenticação depois da instalação

O bootstrap não copia credenciais. Configure cada serviço na sessão nova.

### Git e GitHub CLI

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@example.com"
gh auth login --hostname github.com --git-protocol ssh --web
gh auth setup-git
gh auth status
```

Se uma chave SSH antiga não for restaurada de backup criptografado, gere uma
nova e cadastre a chave pública no GitHub antes de clonar por SSH.

### Open Build Service

O script instala o OSC, define `https://api.opensuse.org`, configura o usuário
OBS `rodrigosbrito` e seleciona o GNOME Keyring como armazenamento de
credenciais. A senha é solicitada separadamente:

```bash
osc config https://api.opensuse.org --change-password
osc my projects
osc ls home:rodrigosbrito:lyra
osc ls home:rodrigosbrito:vega
osc ls home:rodrigosbrito:fina
```

Outro contribuidor pode substituir o usuário durante o bootstrap:

```bash
curl -fsSL https://raw.githubusercontent.com/lyra-os-linux/lyraos-desktop/main/scripts/bootstrap-development.sh \
  | OBS_USER=outro-usuario bash
```

Nunca versione `~/.config/osc/oscrc` ou uma senha do OBS.

### Codex

O Codex é instalado como `@openai/codex` no prefixo de usuário. Autentique com
o fluxo de navegador do ChatGPT:

```bash
codex login
codex login status
```

Também é possível usar o fluxo de dispositivo com `codex login --device-auth`.
Não copie tokens ou `auth.json` para o repositório.

## Projetos do ecossistema

Os comandos abaixo são os caminhos rápidos usados para validar os projetos
que formam a estação Lyra.

### Vega

Vega combina Rust/GTK4/libadwaita com o daemon Go `vegad`:

```bash
cd ~/Git/Vega
cargo fmt --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings

cd vegad
GOCACHE=/tmp/vega-gocache go test ./...
```

Para executar a interface:

```bash
cd ~/Git/Vega
cargo run --manifest-path vega-gtk/Cargo.toml
```

### Beam

```bash
cd ~/Git/Beam
cargo fmt --check
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo run -p beam-gtk
```

### Sulafat

```bash
cd ~/Git/Sulafat
cargo fmt --check
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo run -p sulafat-gtk
```

### Sheliak

```bash
cd ~/Git/Sheliak
npm ci
npm run check
npm run build
npm run pack
```

## Lyra OS e ISO

Build da imagem:

```bash
cd ~/Git/Lyra
./kiwi/test/build-and-run-vm.sh --build-only --published-installer
```

Use o helper: além das validações da ISO, ele monitora e recupera o cache do
carregador de bibliotecas do host durante o bootstrap privilegiado do KIWI.
Não invoque `sudo kiwi-ng system build` diretamente na estação de trabalho.

A versão da imagem é definida somente em `release.toml`. Consulte
[`docs/release-versioning.md`](docs/release-versioning.md) antes de iniciar
uma Beta, RC ou release final.

Boot de teste com disco novo:

```bash
./kiwi/test/build-and-run-vm.sh --fresh-disk
```

Esse modo injeta o instalador compilado do workspace e serve para
desenvolvimento. Para validar exatamente o RPM disponível no OBS:

```bash
./kiwi/test/build-and-run-vm.sh --published-installer
```

Teste com Secure Boot:

```bash
./kiwi/test/build-and-run-vm.sh --fresh-disk --secure-boot
```

O usuário precisa encerrar e iniciar a sessão depois do bootstrap para que os
grupos `kvm` e `libvirt` sejam aplicados.

## Empacotamento no OBS

Faça checkout do pacote e execute o build local a partir da working copy do
OSC. O projeto, repositório e arquitetura devem corresponder ao pacote:

```bash
osc checkout home:rodrigosbrito:lyra NOME-DO-PACOTE
cd home:rodrigosbrito:lyra/NOME-DO-PACOTE
osc build openSUSE_Leap_16.1 x86_64
```

Antes de `osc commit`, confira `osc status`, revise `osc diff` e valide o spec
com rpmlint/spec-cleaner. Nunca envie arquivos de configuração com credenciais.
