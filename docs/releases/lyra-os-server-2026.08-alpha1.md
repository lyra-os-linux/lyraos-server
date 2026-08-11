# Lyra OS Server 2026.08 Alpha 1 — notas de lançamento

O Lyra OS Server Alpha 1 é a primeira imagem pública de avaliação da edição
server do Lyra OS. Ela combina a base openSUSE Leap 16.0 com uma instalação
headless, um instalador interativo em console e as interfaces de administração
do Vega.

Esta é uma versão **Alpha** destinada a testes e homologação. Não é recomendada
para produção nem para máquinas que contenham dados sem backup.

## Destaques

- sistema headless, sem GNOME ou dependências de desktop;
- instalador em console com interface TUI baseada em `dialog`;
- instalação UEFI em disco único com partição ESP e raiz em ext4;
- suporte a Secure Boot pela cadeia assinada do openSUSE (`shim` + GRUB);
- rede configurada automaticamente por DHCP;
- `vegad`, `vega-cli` e `vega-web` instalados e habilitados;
- acesso remoto por SSH habilitado após a instalação;
- firewall ativo, expondo somente SSH e `9090/tcp` para o Vega Web;
- metadados, inventário RPM e SBOMs CycloneDX/SPDX disponíveis junto da ISO.

## Requisitos

- computador ou máquina virtual `x86_64`;
- firmware UEFI — boot BIOS legado não é suportado pelo instalador;
- um disco dedicado que possa ser completamente apagado;
- conexão de rede com DHCP durante e depois da instalação;
- mídia USB ou unidade virtual com capacidade superior ao tamanho da ISO.

## Instalação

1. Inicialize a máquina pela ISO em modo UEFI.
2. Aguarde o login automático da sessão live e a abertura do instalador.
3. Escolha idioma, teclado, fuso horário, hostname e disco de destino.
4. Crie o usuário administrador e confirme a operação destrutiva.
5. Ao final, remova a mídia e reinicie no sistema instalado.

O instalador apaga assinaturas e a tabela de partições do disco selecionado.
Confira cuidadosamente o dispositivo antes de confirmar. Não há opção de
preservar partições ou instalar lado a lado nesta versão.

Após o primeiro boot, o servidor pode ser administrado pelo console, por SSH,
por `vega-cli` ou pelo Vega Web em `http://<endereço-do-servidor>:9090`.

## O que não está incluído

- ambiente gráfico, navegador, Flatpak, CUPS ou aplicativos desktop do Lyra;
- RAID, LVM, Btrfs, Snapper ou rollback do sistema;
- instalação em múltiplos discos ou preservação de partições existentes;
- configuração de IP estático durante a instalação;
- instalação automatizada ou arquivo de respostas;
- suporte a BIOS legado ou ARM64.

## Limitações conhecidas

- a seleção inicial de idioma, teclado e fuso horário contém somente as opções
  essenciais de português do Brasil e inglês/UTC;
- a cobertura inicial prioriza VM/QEMU; a matriz de hardware físico ainda é
  limitada e combinações diferentes de controladoras, firmware e placas de
  rede podem apresentar problemas;
- a raiz usa ext4 e não oferece snapshots nem recuperação por rollback;
- IP estático, VLANs e outras configurações avançadas de rede devem ser feitas
  após a instalação;
- por ser a primeira Alpha, mensagens de diagnóstico e alguns detalhes da TUI
  ainda podem mudar antes da Beta.

Não há credencial padrão. A senha é definida durante a instalação, a conta
`root` permanece bloqueada para login direto e o usuário criado pertence ao
grupo administrativo `wheel`.

## Integridade da imagem

Arquivo esperado:

```text
lyra-os-server.x86_64-2026.08-alpha1.iso
```

Verifique o arquivo usando o `*.iso.sha256` distribuído junto da ISO:

```sh
sha256sum -c lyra-os-server.x86_64-2026.08-alpha1.iso.sha256
```

Para uma publicação oficial, verifique também a assinatura destacada
`*.iso.sha256.asc` com a chave documentada em
`docs/release-signing-key.asc`. Uma imagem sem essa assinatura deve ser
tratada como build de teste.

## Relato de problemas

Ao relatar um problema, inclua o modelo da máquina ou configuração da VM, modo
de firmware, etapa em que ocorreu a falha e os logs disponíveis. Não publique
senhas, chaves, endereços privados ou outros dados sensíveis.

O contrato completo de go/no-go e as evidências exigidas estão em
`docs/server-release-gate.md`.
