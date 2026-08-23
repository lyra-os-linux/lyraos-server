# Versionamento e rastreabilidade de releases

O arquivo [`release-server.toml`](../release-server.toml) é a única fonte
editável da identidade de uma release do Lyra OS Server. Não altere versões
diretamente no KIWI ou no arquivo gerado
`kiwi/root/usr/lib/lyra-os/server-release`.

## Convenção

O Server usa uma versão de calendário `AAAA.MM` e acrescenta o estágio
enquanto a imagem ainda é uma pré-release:

| Estágio | `release-server.toml` | Versão, tag e exemplo de ISO |
|---|---|---|
| Alpha | `stage = "alpha"`, `iteration = N` | `2026.08-alphaN`, `server-v2026.08-alphaN`, `lyra-os-server.x86_64-2026.08-alphaN.iso` |
| Beta | `stage = "beta"`, `iteration = N` | `2026.08-betaN`, `server-v2026.08-betaN`, `lyra-os-server.x86_64-2026.08-betaN.iso` |
| RC | `stage = "rc"`, `iteration = N` | `2026.08-rcN`, `server-v2026.08-rcN`, `lyra-os-server.x86_64-2026.08-rcN.iso` |
| Final | `stage = "release"`, `iteration = 0` | `2026.08`, `server-v2026.08`, `lyra-os-server.x86_64-2026.08.iso` |

## Contrato de maturidade

As datas do cronograma são limites de planejamento, não autorização para
promover um produto que ainda não atingiu o estágio seguinte. Se necessário,
o lançamento atrasa. O objetivo não é alegar perfeição, mas entregar uma
distribuição previsível e "chata de tão confiável": ela deve poder ser usada
diariamente por um período prolongado sem travar, degradar, exigir manutenção
recorrente ou interromper o trabalho do usuário.

| Estágio | Estado esperado | Mudanças permitidas |
|---|---|---|
| Alpha | Produto em construção e qualificação | Funcionalidades planejadas, integração e correções, sempre com estabilidade em primeiro lugar. |
| Beta | Escopo completo e funcionalmente congelado | Correções de bugs, regressões, segurança, desempenho, acessibilidade e traduções existentes. |
| RC | Produto já estável; candidato completo sob verificação final | Nenhuma mudança rotineira. Defeito não trivial interrompe a promoção, devolve o produto à estabilização e exige uma nova RC. |
| Estável | Conteúdo funcional publicado e congelado | Correções de bugs, travamentos, segurança e melhorias de performance crítica quando necessárias (ver [`AGENTS.md`](../AGENTS.md)). Demais mudanças seguem para o próximo ciclo completo. |

A promoção para RC afirma que os gates de estabilidade já estão verdes; a RC
não é uma Beta com outro nome. A promoção para estável confirma o mesmo
conteúdo após a última verificação de imagem, assinatura, instalação,
atualização e uso real. Ausência de P0/P1 é requisito mínimo, não evidência
suficiente por si só.

Uma nova compilação da mesma release mantém a versão. O commit, a data, o
estado limpo ou modificado da árvore e o SHA-256 distinguem builds e ficam no
manifesto `*.iso.manifest.json` criado pelo helper de build.

## Preparação de uma versão

1. Edite apenas os campos em `release-server.toml`.
2. Renderize os consumidores versionados:

   ```bash
   ./scripts/server-release.py render
   ```

3. Revise as mudanças e execute as validações:

   ```bash
   ./scripts/server-release.py check
   python3 -m pytest tests/ -v
   ```

4. Faça o build pelo helper (`scripts/image-build.py export`/`validate`). Ele
   rejeita metadados divergentes, um nome de ISO inesperado e um `VERSION_ID`
   incorreto dentro da imagem.

5. Somente um commit limpo e aprovado deve originar uma imagem publicada.
   Crie a tag derivada de `release-server.toml` no commit exato e use a mesma
   versão no título das notas de release. O campo pode ser consultado sem
   duplicar a regra:

   ```bash
   ./scripts/server-release.py field tag
   ./scripts/server-release.py field iso_filename
   ```

As notas devem registrar o nome da ISO, o SHA-256 e os campos `built_at` e
`source.commit` do manifesto. Uma árvore marcada como `source.dirty: true` é
adequada para desenvolvimento local, mas não para publicação.

## Lyra OS Server 1.0 "Delos"

**Delos** é o codinome de produto deste ciclo do Server. Ele não é acrescentado
ao schema mecânico de `release-server.toml`, aos nomes de pacote nem ao volume
da imagem. O Server segue os mesmos critérios de promoção e a mesma cadência
descritos acima: Alphas de até 3 semanas, Betas de até 4 semanas, RCs de até 2
semanas e buffer final de 2 semanas. Uma etapa fecha quando seus gates ficam
verdes; as datas são teto, não motivo para promover uma imagem com P0/P1
aberto.

| Estágio | Cadência | Datas | Objetivo de saída |
|---|---|---|---|
| alpha1 | 3 semanas | 11/ago/2026 → 01/set/2026 | Reconfirmar instalação completa após os últimos ajustes da TUI e produzir o primeiro candidato rastreável. |
| alpha2 | 3 semanas | 01/set/2026 → 22/set/2026 | Consolidar a integração do fluxo Server e preparar as correções e evidências do gate seguinte. |
| alpha3 | cancelada | — | Etapa absorvida pela Beta 1 por decisão do mantenedor em 15/08/2026. |
| beta1 | em andamento | desde 15/ago/2026 | Congelamento funcional, correção dos bloqueadores e validação do fluxo suportado em disco inteiro/ext4. |
| beta2 | 4 semanas | 10/nov/2026 → 08/dez/2026 | Estabilidade, atualização dos pacotes, rede e administração remota em execuções repetidas. |
| beta3 | 4 semanas | 08/dez/2026 → 05/jan/2027 | Internacionalização dos componentes próprios aplicáveis ao Server e fechamento da documentação operacional. |
| rc1 | 2 semanas | 05/jan/2027 → 19/jan/2027 | Candidato completo, assinado e exercitado em VM e hardware físico, sem P0/P1. |
| rc2 | 2 semanas | 19/jan/2027 → 02/fev/2027 | Somente correções bloqueantes e repetição integral do gate. |
| final (buffer) | 2 semanas | 02/fev/2027 → **~16/fev/2027** | Publicação da Lyra OS Server 1.0 "Delos" e verificação dos artefatos baixados. |

O mantenedor encerrou o desenvolvimento funcional e iniciou a Beta 1 em
15/08/2026. O conteúdo antes atribuído à Alpha 3 ficou restrito a correções
bloqueantes, estabilização e evidências dentro da Beta 1. O Server
não precisa esperar o Desktop nem ser publicado no mesmo dia; cada edição só
avança com o próprio gate verde. Mantida essa antecipação nas etapas seguintes,
o alvo antecipado da final permanece em **~26/jan/2027**; o buffer integral
continua até aproximadamente 16/02/2027.

### Estado na entrada da Alpha 1

O fluxo boot live → TUI → disco inteiro/GPT/ESP/ext4 → chroot → shim/GRUB →
primeiro boot já completou em VM, com DHCP, SSH, `vegad` e `vega-web` ativos.
Os testes locais de shell, comportamento da TUI, segurança de senha/sudo e
identidade do overlay estão verdes. Permanecem como bloqueadores para sair da
Alpha 1:

- repetir o fluxo ponta a ponta depois das correções finais do gauge e do
  nível de log do console;
- validar Secure Boot e os argumentos reais de `shim-install` no candidato;
- gerar ISO, checksum, assinatura, inventário, SBOMs e manifesto de evidência
  a partir de uma árvore limpa;
- registrar a matriz de hardware, incluindo ao menos o risco explícito da
  cobertura física disponível.

## Lyra OS Server 1.1 "Tebas"

O ciclo Server 1.1 usa o codinome de produto **Tebas** e faz o rebase para
openSUSE Leap 16.1. O codinome não altera o schema mecânico de
`release-server.toml`, os nomes de pacote ou o volume da imagem.

| Estágio | Cadência | Datas | Objetivo de saída |
|---|---|---|---|
| alpha1 | 3 semanas | 01/mar/2027 → 22/mar/2027 | Requalificar build, instalação e primeiro boot sobre Leap 16.1. |
| alpha2 | 3 semanas | 22/mar/2027 → 12/abr/2027 | Fechar Secure Boot, rede, firewall e administração remota na nova base. |
| alpha3 | 3 semanas | 12/abr/2027 → 03/mai/2027 | Resolver bloqueadores e completar a matriz de hardware sem ampliar escopo. |
| beta1 | 4 semanas | 03/mai/2027 → 31/mai/2027 | Congelamento funcional e validação repetida do fluxo suportado. |
| beta2 | 4 semanas | 31/mai/2027 → 28/jun/2027 | Estabilidade, atualizações, rede e administração remota. |
| beta3 | 4 semanas | 28/jun/2027 → 26/jul/2027 | QA linguístico, documentação operacional e correções finais. |
| rc1 | 2 semanas | 26/jul/2027 → 09/ago/2027 | Candidato completo, assinado e exercitado em VM e hardware. |
| rc2 | 2 semanas | 09/ago/2027 → 23/ago/2027 | Somente bloqueadores P0/P1 e repetição integral do gate. |
| final estável (buffer) | 2 semanas | 23/ago/2027 → **~06/set/2027** | Publicação do Lyra OS Server 1.1 "Tebas" e verificação dos artefatos. |

## Campos sincronizados

O renderizador (`scripts/server-release.py`) mantém alinhados:

- `<version>` e volume ID do KIWI;
- nome produzido para a ISO;
- `PRETTY_NAME`, `VERSION_ID`, `BUILD_ID`, `IMAGE_ID` e `IMAGE_VERSION` em
  `/etc/os-release`.

O CI deve executar o modo `check` e os testes. Assim, editar um arquivo
gerado sem alterar o manifesto, ou esquecer de renderizar uma mudança de
release, torna o job vermelho.
