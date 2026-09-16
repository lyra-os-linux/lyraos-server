# NVIDIA opcional no Server/ext4

Decisão aprovada em 16/09/2026: incluir agora a instalação pelo Vega CLI e
Vega Web, com recuperação no layout ext4 simples. O Server mantém o instalador
em disco único e não ganha um sistema geral de snapshots/rollback.

- **CLI:** Hardware e Kernel → NVIDIA.
- **Web:** Hardware e Kernel → NVIDIA; diagnóstico sem reautenticação,
  confirmação e senha administrativa apenas ao instalar. O broker usa o UID
  real do usuário e Polkit; o serviço de rede nunca instala como root.
- Ambos explicam status e recuperação em português, inglês e espanhol.
- Requer vegad >= 5.1.29, Restic >= 0.17, conexão aos repositórios, GPU/base/kernel
  qualificados e espaço livre. A receita inclui Restic também no ambiente live.
- A instalação usa os RPMs oficiais NVIDIA 610.57.04 e KMP assinado pela SUSE,
  com o pacote de integração `lyra-nvidia`. Não usa `.run`, DKMS, remoção automática
  de drivers antigos ou kernel novo sem qualificação.

Antes do commit RPM, dentro do lock do mesmo Zypper, o vegad prepara uma cópia
local criptografada de `/usr`, `/etc`, `/boot` sem ESP e `/var/lib/alternatives`,
exporta a base RPM e verifica todos os dados. Se isso falhar, a instalação é
recusada. Dados de serviços, pasta pessoal e logs não fazem parte da cópia.
Não é proteção contra perda física do disco.

A recuperação exige iniciar outra mídia de recuperação compatível e montar a
raiz ext4 original em `/mnt`, sem mounts internos nem ESP. Use a referência
mostrada pelo Vega, após conferir o ponto e seu horário. Como administrador:

```sh
sudo /usr/lib/vega/vegad nvidia-recover --target /mnt --reference REFERENCIA --confirm
```

A restauração verifica UUID/máquina, permissões e integridade. Substitui somente
os diretórios do sistema cobertos, remove arquivos novos neles e importa uma
base RPM consistente. Preserva dados de serviços/home/ESP. Uma cópia antiga
reverte também atualizações posteriores do sistema: revise o impacto nos
aplicativos e seus dados antes de reutilizá-la.

Não existe restauração do sistema em uso pela Web. Uma interrupção deixa um
marcador `recovery-required`; permaneça no ambiente de recuperação e repita o
comando até concluir. O backend remove somente locks que o Restic considere
obsoletos. Detalhes de falhas ficam root-only em `last-error.txt` dentro do ponto.

A API e os limites estão em
[vegad/docs/nvidia.md](https://github.com/lyra-os-linux/vegad/blob/main/docs/nvidia.md).
A imagem seguinte deve incluir os RPMs atualizados, e a ISO completa continua
sujeita aos gates de live, instalação, primeiro boot e hardware real. Testar a
VM de recuperação não substitui GPU física, Secure Boot, CUDA ou a ISO final.

## Validação local de 16/09/2026 e próxima ISO

- Dez RPMs NVIDIA instalados em VM Leap/ext4 com scripts normais e criação da
  recuperação dentro do callback anterior ao commit do Zypper.
- Falhas deliberadas em arquivos do sistema, restauração offline, interrupção
  real durante o restore, retomada e repetição passaram. Após boot, inventário
  RPM exatamente igual ao anterior; dados de serviços/home/ESP preservados.
- Recusas de alvo errado, raiz ativa, manifesto/export corrompido, chave
  insegura, symlink e mount inesperado passaram.
- RPMs finais vegad5.1.29, CLI5.1.23 e Web5.1.23 instalados juntos na VM;
  HTTPS/PAM, consultas públicas, três idiomas e CSRF verificados.
- Receita/instalador/artefatos: 113 testes, três ignorados.

Evidência consolidada: [nvidia-clients-server-20260916.json](evidence/nvidia-clients-server-20260916.json).
As fontes e os RPMs estão locais; publicação ainda pendente. Não há ISO nova
qualificada. Na próxima candidata, confirmar vegad>=5.1.29, CLI/Web>=5.1.23 e
Restic>=0.17 no live e no instalado; repetir instalação/recuperação a partir
da própria mídia e validar GPU real, Secure Boot, CUDA quando aplicável.
A arquitetura reutiliza Zypper/RPM/Restic; restringe a recuperação ao ext4
simples e impede a instalação quando o ponto não puder ser verificado.
Reversão do lote de software: reinstalar os RPMs anteriores; não excluir
pontos de recuperação ainda necessários. Isso não reverte o driver.
