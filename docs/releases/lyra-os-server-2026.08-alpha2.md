# Lyra OS Server 2026.08 Alpha 2 — notas de lançamento

A Alpha 2 consolida a instalação e o primeiro boot da edição Server do Lyra
OS, baseada no openSUSE Leap 16.0. É uma versão de avaliação, não recomendada
para produção nem para discos que contenham dados sem backup.

## Destaques

- instalador TUI disponível em português do Brasil e inglês;
- mensagens de progresso e diagnóstico no idioma selecionado;
- quatro instalações consecutivas validadas pelo mantenedor;
- boot UEFI validado com Secure Boot ligado e desligado;
- raiz ext4, usuário administrativo com `sudo` e conta root bloqueada;
- DHCP, SSH, `vegad` e `vega-web` ativos após o primeiro boot;
- firewall expondo somente SSH e `9090/tcp`;
- coletores schema 1 para sessão live, primeiro boot e Secure Boot;
- logs de falha com estágio, status e comando, sem registrar a senha.

## Requisitos e instalação

É necessário um computador ou VM `x86_64`, firmware UEFI, rede DHCP e um
disco dedicado que possa ser completamente apagado. Inicialize pela ISO,
escolha idioma, teclado, fuso, hostname, disco e usuário administrativo. Ao
final, remova a mídia e reinicie pelo disco instalado.

O instalador não preserva partições e não oferece instalação lado a lado.

## Escopo e limitações

- sem ambiente gráfico ou aplicativos Desktop;
- sem RAID, LVM, Btrfs, Snapper ou rollback;
- sem configuração de IP estático durante a instalação;
- sem BIOS legado ou ARM64;
- idiomas do instalador Server limitados a português do Brasil e inglês;
- cobertura aceita nesta Alpha concentrada em VM/QEMU; hardware físico
  diverso permanece como risco residual documentado.

Não existe senha padrão. A senha é criada durante a instalação, o usuário
pertence ao grupo `wheel` e o login direto de root permanece bloqueado.

## Integridade

Arquivo esperado:

```text
lyra-os-server.x86_64-2026.08-alpha2.iso
```

Verifique o checksum:

```sh
sha256sum -c lyra-os-server.x86_64-2026.08-alpha2.iso.sha256
```

Conforme a ADR 0005, as versões Alpha não possuem assinatura destacada da
ISO. Ela se torna obrigatória a partir da Beta 1.

O gate completo e os riscos aceitos estão em `docs/server-release-gate.md`.
