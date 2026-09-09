# Limpeza após falha do instalador Server

Relacionada à [issue #19](https://github.com/lyra-os-linux/lyraos-server/issues/19).
Antes desta correção, falhas na montagem da ESP, na cópia com `tar` ou nos
bind mounts podiam terminar a tentativa com o destino ainda montado. O handler
de limpeza só era ativado depois de todos os bind mounts; `fail` não o chamava.

O worker do instalador agora registra um handler `EXIT` antes da primeira
tentativa de montagem. Ele atende erros, saídas explícitas e os sinais HUP,
INT, TERM e PIPE. Cada destino é registrado antes de executar `mount`, para
cobrir também uma montagem concluída pelo kernel antes de uma interrupção.
Pontos que já estavam montados são recusados e não entram nessa lista.
A limpeza percorre as tentativas em ordem inversa, verifica quais continuam
montadas e tenta desmontá-las sem opções lazy/force.

Uma falha da limpeza é registrada junto ao erro inicial, sem substituir seu
código de saída. Se apenas a limpeza falhar, a instalação também falha.
Os códigos dos dois processos de `tar` são capturados dentro do pipeline;
uma falha do produtor tem precedência sobre o erro de arquivo truncado do
leitor, enquanto SIGPIPE do produtor dá precedência à falha do leitor.
Ambos ficam no log. O processo principal preserva o status do worker e
também recusa sucesso quando o `dialog --gauge` falha. O nível de mensagens
do console é restaurado na saída normal e nos sinais tratados.

## Validação

`python3 -m unittest discover -s tests -v` executa os contratos existentes e
o worker extraído do script distribuído com comandos externos controlados.
As duas cópias (`scripts/server-install.sh` e a cópia no overlay KIWI) devem
continuar idênticas. Os cenários cobrem:

- Falha em cada uma das nove montagens, antes e depois de a montagem ocorrer.
- Falhas dos dois lados da cópia, SIGPIPE e arquivo `tar` inválido.
- HUP/INT/TERM após preparação parcial e durante a cópia, além de sinais ao
  grupo de processos enquanto há um comando de primeiro plano em execução.
- Erro de configuração, limpeza com falha, saída prematura/erro do gauge,
  montagem preexistente preservada e uma nova tentativa depois de falha.

O runner `scripts/check-server-mount-vm.py` repete esses cenários em QEMU e
acrescenta um destino realmente ocupado por outro processo. São 55 execuções
de cenário em 12 testes, com discos ext4/FAT descartáveis. As asserções leem
`/proc/self/mountinfo`, verificam a ausência de montagens residuais nos casos
que permitem desmontagem e preservam os mounts de origem da sessão da VM.
Nos casos deliberadamente ocupados ou com falha de `umount`, verificam o erro
e a montagem restante antes de desmontar a fixture.

Exemplo (kernel legível e diretório de módulos correspondente):

```sh
python3 scripts/check-server-mount-vm.py \
  --kernel /caminho/vmlinuz \
  --modules-dir /lib/modules/VERSAO \
  --log /tmp/server-mount-vm.log
```

O runner usa TCG, sem rede ou discos do host. Antes de formatar, a suíte exige
um marcador na linha de comando do kernel e os números de série específicos
dos dois discos virtuais. Os programas e módulos do host são apenas copiados
para o initramfs; módulos são carregados exclusivamente dentro da VM.
A CI executa essa VM e ShellCheck além dos contratos.

## Limites e reversão

A VM é um teste de recuperação das montagens, não uma instalação completa da
ISO. Particionamento e configuração em chroot são substituídos na fixture;
a árvore EFI de sysfs e efivarfs usam substitutos com bind mount/tmpfs porque
o boot direto do kernel não oferece NVRAM UEFI. Isso não qualifica firmware,
Secure Boot, bootloader ou primeiro boot. Antes de publicar uma imagem com
essa correção, executar novamente a instalação completa e o gate Server.

SIGKILL, queda de energia e processos presos no kernel não garantem limpeza.
Se o destino permanecer ocupado, o log identifica as montagens que falharam;
a tentativa não produz resultado de sucesso. A correção não tenta desfazer
particionamento ou restaurar o conteúdo anterior do disco.

Em caso de regressão, interromper a publicação do candidato e reverter o
commit nas duas cópias do instalador, mantendo o último artefato qualificado.
Revalidar a recuperação e a instalação completa antes de gerar outra imagem.
