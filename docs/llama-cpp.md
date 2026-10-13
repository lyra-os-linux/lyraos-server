# llama.cpp e variantes do Lyra Server

Status: planejamento aprovado; implementação pendente. Acompanhamento: [Server #21](https://github.com/lyra-os-linux/lyraos-server/issues/21).

Disponibilizar **llama.cpp no Lyra OS Server**, com pacotes RPM distribuídos pelo **OBS**, inferência local sem interface gráfica e servidor HTTP integrado ao systemd.

## Decisões aprovadas pelo mantenedor

- **Duas ISOs do Lyra Server:** uma padrão **sem llama.cpp** e outra **com llama.cpp e driver NVIDIA pré-instalados**. A segunda deve entregar também o backend CUDA e as bibliotecas necessárias para executar inferência acelerada; instalar apenas o driver não atende à finalidade da imagem.
- Manter RPM/OBS como forma de instalação e atualização dos pacotes. As **ISOs são construídas localmente**, seguindo o processo Lyra.
- Manter inferência em CPU disponível, inclusive para diagnóstico e recuperação. O pacote CPU instalado separadamente não deve obrigar a instalar driver NVIDIA.
- Princípio do privilégio mínimo: instalação e alterações administrativas podem exigir autorização; inferência, consultas e o processo servidor não executam como root.

Nomes comerciais/arquivos das duas imagens, versão upstream, arquiteturas e marco de release serão definidos durante a implementação. A decisão de produzir as duas variantes já está tomada. Esta issue planeja a entrega; não significa que pacotes ou imagens já estejam prontos.

## Levantamento da documentação oficial

Leitura em **15/09/2026**, com cópia de referência no commit [`d1d3c3396aa13a5f239109a822666c4870490ad5`](https://github.com/ggml-org/llama.cpp/tree/d1d3c3396aa13a5f239109a822666c4870490ad5). Esse commit identifica a documentação consultada, **não é ainda a versão escolhida para distribuição**. Confirmar cada recurso na versão empacotada.

### 1. Projeto, instalação e licença

O projeto implementa inferência em C/C++, com execução em CPU, GPU e combinações das duas. Há modelos quantizados e diferentes backends. A documentação apresenta ferramentas locais e um servidor HTTP; o software utiliza licença MIT, enquanto componentes incorporados e modelos precisam de análise própria. As alternativas de instalação upstream incluem pacotes de outros ecossistemas, mas a entrega Lyra será nativa RPM. [Projeto](https://github.com/ggml-org/llama.cpp/tree/d1d3c3396aa13a5f239109a822666c4870490ad5), [licença](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/LICENSE), [instalação](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/install.md).

**Ações Lyra:**

- Investigar primeiro o empacotamento openSUSE existente; reutilizar o que atender a versão, manutenção e compatibilidade exigidas.
- Registrar tag/commit, origem e hashes das fontes, dependências incorporadas e respectivas licenças.
- Definir nomes dos RPMs, bibliotecas compartilhadas, ferramentas CLI, servidor e subpacotes de backends sem colisões com a base.
- Publicar uma tabela de comandos realmente instalados. O README atual usa exemplos `llama cli` / `llama serve`, enquanto outras páginas ainda usam `llama-cli` / `llama-server`; os exemplos Lyra devem ser executados contra o RPM escolhido.
- Ferramentas de conversão/quantização e dependências Python, se distribuídas, ficam separadas do serviço mínimo.

### 2. Compilação e portabilidade

O build usa CMake. CUDA é habilitado com `GGML_CUDA`, requer toolkit e permite definir `CMAKE_CUDA_ARCHITECTURES`. A documentação orienta desabilitar `GGML_NATIVE` em builds CUDA não nativos. Há backends carregáveis com `GGML_BACKEND_DL`. OpenSSL habilita HTTPS/TLS; o build pode terminar sem SSL se essa dependência faltar. OpenBLAS pode ajudar no processamento do prompt, sem a mesma promessa para geração. Vulkan requer dependências de compilação próprias, incluindo cabeçalhos SPIR-V. [Build oficial](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/build.md).

**Ações Lyra:**

- Fixar baseline de CPU e flags explícitas; testar em processador compatível com esse mínimo. Desabilitar otimizações nativas não dispensa conferir as demais instruções geradas.
- Separar dependências de build das de execução; não exigir compilador/toolkit completo na máquina que apenas faz inferência.
- Fazer build sem downloads implícitos e sem depender da GPU do trabalhador OBS. Levar todas as fontes necessárias ao pacote, inclusive ativos web quando incluídos.
- Declarar e verificar SSL no RPM. Qualificar combinação compilador, glibc, toolkit CUDA, driver e arquitetura da GPU.
- Preferir subpacotes ou carregamento de backend que preservem a instalação CPU sem bibliotecas CUDA obrigatórias.
- CUDA é requisito da ISO com llama.cpp/NVIDIA. Vulkan, HIP/ROCm e SYCL são possibilidades futuras, sujeitas a hardware, dependências e testes; não são promessas desta primeira entrega.

### 3. Modelos, downloads e funcionamento offline

O formato esperado é **GGUF**. É possível usar arquivo local ou obter modelos com `-hf`; outros formatos podem exigir conversão pelos scripts do projeto. Quantização altera o tamanho dos pesos e pode afetar qualidade e desempenho. [Modelos](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/models.md).

**Ações Lyra:**

- Não embutir pesos grandes nem executar downloads nos scriptlets RPM. Prever escolha e obtenção explícita do modelo após instalação, com instruções também para importação offline.
- Escolher modelo pequeno para qualificação e registrar origem, revisão, arquivo, quantização, licença, tamanho e hash. Um arquivo GGUF não garante sozinho arquitetura suportada pela versão instalada.
- Separar diretório de modelos, cache, configuração e executáveis; propor caminhos gerenciáveis em `/var/lib` e `/etc`, preservando dados do administrador em atualizações/remoções.
- Descrever consumo de RAM/VRAM medido por modelo e configuração, incluindo contexto, cache KV, concorrência e processamento em lote. Não usar apenas o tamanho do arquivo para anunciar requisitos mínimos.
- Proteger credenciais de download, documentar modelos com acesso restrito e evitar tokens em logs ou na linha de comando.
- Testar inferência com rede indisponível depois de importar o modelo. A imagem pré-instalada só ficará pronta para responder após existir modelo válido e configuração concluída; isso deve ser claro na documentação.

### 4. API e recursos do servidor

O servidor documenta interface web, rotas compatíveis com OpenAI para chat, completions, responses e embeddings, além de Messages compatível com Anthropic, reranking, streaming, processamento concorrente, batching e saída JSON com restrições. Há configuração de host, porta, contexto, threads e slots. `/health` não exige chave; métricas Prometheus são opcionais. Arquivo de chaves, modo offline, presets, cache e gerenciamento de modelos também aparecem na documentação. Compatibilidade deve ser validada por rota/modelo; não equivale a reproduzir integralmente os serviços citados. [Servidor](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/tools/server/README.md).

**Ações Lyra:**

- Entrega mínima: CLI, carregamento de modelo local, health/readiness, informação de modelo, chat HTTP e streaming, com exemplos executáveis e tratamento de erro.
- Qualificar embeddings e reranking com modelos apropriados antes de anunciá-los. Registrar quais rotas foram testadas e quais recursos permanecem experimentais/opcionais.
- Integrar configuração de endereço, porta, modelo, contexto, limite de geração, threads, concorrência, timeout e limites de memória adequados ao equipamento.
- Serviço inicia em loopback, sem abertura automática de firewall. Métricas, slots e interfaces administrativas só são expostos quando configurados para o ambiente adequado.
- Definir política de logs e retenção; não registrar prompts, respostas, tokens de autenticação ou dados dos modelos por padrão.
- Interface web, quando incluída, deve funcionar com os ativos empacotados e em instalação sem rede externa.

### 5. Serviço, segurança e operação

O upstream recomenda isolamento para modelos/entradas não confiáveis e aponta limites relevantes em redes não confiáveis e ambientes com múltiplos clientes. Sua política exclui determinadas funções e a interface web da cobertura de segurança; também contém orientações de divulgação conflitantes que precisam ser conferidas novamente ao reportar um problema. Não tratar chave de API como isolamento entre clientes. [Política de segurança](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/SECURITY.md).

**Ações Lyra:**

- Serviço systemd com usuário dedicado, permissões mínimas de leitura dos modelos e acesso somente aos dispositivos GPU necessários.
- Aplicar restrições de filesystem, privilégios, recursos e rede que sejam compatíveis com CPU e CUDA; testar as restrições, evitando bloquear a GPU por acidente.
- Configuração ausente/modelo inválido deve produzir diagnóstico claro, sem ciclos infinitos de reinício. Ativar início automático somente após configuração válida.
- Para acesso remoto, documentar autenticação, TLS, rede controlada, limites de requisição e isolamento. Não oferecer exposição direta à Internet como configuração padrão ou qualificada apenas por existir uma chave.
- Manter RPC, router com administração remota de modelos e MCP fora da configuração inicial. Se desejados depois, abrir subtarefas com justificativa, isolamento e validação próprios.
- Separar instâncias/clientes quando houver necessidade de isolamento de dados; não compartilhar cache de conversação como se fosse uma barreira de segurança.
- Documentar start/stop/restart/status, logs, troca de modelo, backup, restauração, atualização e recuperação sem apagar os modelos locais.

### 6. Recursos avançados encontrados e limites da entrega

| Recurso documentado | Tratamento proposto para Lyra |
| --- | --- |
| Function calling e templates de chat | Depende de modelo/template e opções como Jinja. Validar separadamente; chamadas geradas pelo modelo não autorizam executar comandos administrativos. [Documentação](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/function-calling.md). |
| Multimodalidade com `libmtmd` | Há entrada de imagem, áudio e vídeo para modelos suportados, possivelmente com projetor `mmproj`. Registrar como expansão; selecionar modelo, arquivos e casos de teste antes de anunciar suporte. [Documentação](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/multimodal.md). |
| Múltiplas GPUs | Seleção de dispositivos, divisão por camadas e modos adicionais; paralelismo tensorial tem limitações e caráter experimental. NCCL e P2P exigem qualificação; P2P pode causar falhas em determinadas plataformas. Primeiro validar uma GPU. [Documentação](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/multi-gpu.md). |
| Speculative decoding | Métodos com modelo auxiliar ou reaproveitamento de padrões podem acelerar cenários específicos. Medir consumo, qualidade e desempenho antes de ativar. [Documentação](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/speculative.md). |
| Presets INI | Avaliar como configuração reproduzível de modelos e parâmetros, validando precedência e compatibilidade da versão. [Documentação](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/preset.md). |
| Contêineres e outros backends | Referências úteis para ambientes de teste ou expansão; distribuição solicitada continua RPM/OBS. Conferir diferenças reais entre backends antes de declarar equivalência. [Contêineres](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/docker.md), [operações por backend](https://github.com/ggml-org/llama.cpp/blob/d1d3c3396aa13a5f239109a822666c4870490ad5/docs/ops.md). |

## Vega Web para administrar llama.cpp

O mantenedor solicitou configurações do llama.cpp no Vega Web e definiu sua habilitação automática conforme hardware/software instalados. A direção recomendada é **reutilizar o Vega Web existente com um módulo/perfil Server**, preservando a base de código e o contrato com `vegad` e `lyra-vega-dbus`. Avaliar um subpacote ou edição específica somente se houver necessidade concreta; não decidir antecipadamente por um fork ou outro aplicativo.

### Regra de detecção e habilitação aprovada

O backend deve identificar se **a máquina administrada possui GPU NVIDIA** e se **llama.cpp está instalado**. Quando as duas condições forem verdadeiras, o Vega Web habilita os grupos de configuração **Placa gráfica/NVIDIA** e **IA/llama.cpp**. A informação vem do servidor, não da GPU do computador/navegador que acessa o painel.

| Hardware NVIDIA | llama.cpp instalado | Comportamento dos novos grupos |
| --- | --- | --- |
| Sim | Sim | Habilitar configuração NVIDIA e IA para usuários autorizados. |
| Sim | Não | Não habilitar esses novos grupos completos; informar que llama.cpp não está instalado. |
| Não | Sim | Não habilitar o conjunto NVIDIA + IA; manter diagnóstico e uso CPU já disponíveis por outros meios. |
| Não | Não | Não habilitar os novos grupos; manter o restante do Vega Web funcionando normalmente. |
| Detecção indisponível/erro | Qualquer | Mostrar indisponibilidade do diagnóstico, sem afirmar ausência e sem habilitar ações baseadas em capacidade desconhecida. |

- A presença física da NVIDIA deve ser identificada independentemente de o driver carregar ou de `nvidia-smi` funcionar. GPU detectada com driver ausente/incompatível é um estado a diagnosticar.
- Distinguir llama.cpp instalado de serviço ativo e modelo configurado. Serviço parado ou modelo ausente não deve esconder os controles necessários para configurar e iniciar.
- Mostrar separadamente driver, compatibilidade módulo/bibliotecas, CUDA disponível e backend efetivo. Não declarar aceleração pronta somente porque existe hardware ou pacote instalado.
- Atualizar a detecção após instalação/remoção de pacotes ou mudanças relevantes, sem exigir reinício do Vega Web para refletir capacidades. Tratar desaparecimento de capacidade entre a leitura e a ação.
- Habilitação por capacidades não concede privilégios: aplicar autenticação e autorização no backend em cada ação administrativa. A API deve rejeitar ações sem suporte/autorização mesmo se alguém contornar a interface.
- Consultas de hardware/pacotes/estado não pedem elevação a root. Se uma inspeção não estiver disponível, retornar estado explicativo em vez de abrir uma autenticação administrativa ao carregar a página.

O Vega Web atual já fornece acesso HTTPS em LAN, login do sistema e um fluxo de reautenticação para operações administrativas. A integração deverá seguir essa arquitetura, sem passar comandos arbitrários de formulários ao shell. [Vega Web](https://github.com/lyra-os-linux/vega-web), [arquitetura](https://github.com/lyra-os-linux/vega-web/blob/main/docs/architecture.md), [autorização](https://github.com/lyra-os-linux/vega-web/blob/main/docs/web-authorization.md).

**Escopo a detalhar antes da implementação:**

- Painel de estado: versão, modelo carregado, serviço, endpoint, backend efetivamente usado e disponibilidade da GPU, RAM/VRAM e erros relevantes.
- Seleção/importação de modelo GGUF existente; eventual download deve mostrar origem, licença, tamanho e destino, com operação explícita e progresso. Acesso aos arquivos limitado aos diretórios autorizados.
- Configuração de CPU/CUDA, GPU selecionada, camadas descarregadas para GPU, contexto, threads, concorrência e limites de recursos, com validação de valores e aviso quando exigir reinício.
- Start/stop/restart, ativação no boot, alteração de configuração e credenciais somente por ações administrativas autenticadas e autorizadas. Abrir o painel, consultar estado ou realizar inferência permitida não deve pedir elevação a root.
- Endereço/porta e configuração de acesso à API, mantendo padrão local; segredos protegidos, sem devolvê-los integralmente à interface nem gravá-los em logs.
- Diagnóstico e teste curto de inferência para confirmar CPU/CUDA, com timeout, cancelamento e limites. Acesso web administrativo e autenticação da API de inferência são controles distintos.
- Interface nos idiomas suportados pelo Vega, acessibilidade, estados de modelo ausente/serviço parado e comportamento claro na ISO padrão quando llama.cpp não estiver instalado.
- Aplicação de configuração com validação prévia e recuperação da última configuração válida. Não prometer recuperação por Snapper: o Server atual usa ext4 e não inclui Snapper.
- Pacotes do módulo/edição também via OBS; testar o fluxo completo pela web e os mesmos controles de autorização no backend. A página não constitui a única barreira de segurança.

A regra funcional de detecção/habilitação está aprovada; o desenho final e a divisão entre repositórios/pacotes ainda serão avaliados. Converter essa parte em subtarefas coordenadas de Vega Web, daemon/contratos e Server quando a implementação começar.

## OBS e integração das duas ISOs

1. Definir projeto/repositórios OBS e arquiteturas suportadas; construir primeiro em staging, publicar fontes e RPMs com dependências resolvidas e promover após qualificação.
2. Reaproveitar a mesma receita base do Server, com perfis de imagem explícitos e diferença de pacotes verificável. Evitar duplicar toda a manutenção das imagens.
3. **ISO padrão:** ausência de llama.cpp, seu serviço e dependências exclusivas; validar que a variante de IA não alterou a base por dependência acidental. Documentar instalação posterior dos RPMs.
4. **ISO com llama.cpp + NVIDIA:** pré-instalar CLI, servidor, backend CUDA, bibliotecas de execução e conjunto NVIDIA compatível. Registrar manifestos e versões de kernel, KMP, bibliotecas e CUDA. Não confundir pré-instalação de software com inclusão de pesos.
5. Reutilizar o contrato de integração NVIDIA em preparação para Lyra/openSUSE, sem misturar provedores incompatíveis de módulo e bibliotecas. O resultado local com 610.57.04 é uma referência de investigação, não uma versão definitiva da futura ISO Server.
6. Definir GPUs compatíveis e validar Secure Boot com o módulo correspondente assinado, boot do kernel instalado, initramfs e recuperação. A atualização não pode deixar bibliotecas e módulo incompatíveis silenciosamente.
7. Respeitar separadamente as condições de distribuição dos componentes NVIDIA na ISO e as regras do OBS público; não pressupor que publicar um RPM de integração autoriza hospedar todos os binários proprietários no OBS.
8. Construir as duas ISOs **localmente**, gerar checksums, manifestos e resultados independentes. Testar instalação, primeiro boot e atualização; a imagem com IA precisa de inferência CUDA real em hardware compatível.
9. Validar também CPU e comportamento sem GPU compatível: o sistema deve iniciar, informar a limitação e permitir configuração CPU, sem esconder falhas de aceleração.

## Ordem de implementação e critérios de aceite

- [ ] Escolher versão e reaproveitamento de pacotes openSUSE; registrar licença, dependências, baseline CPU e GPUs suportadas.
- [ ] RPM CPU e ferramentas construídos no OBS; instalação limpa sem puxar driver NVIDIA.
- [ ] Backend CUDA empacotado e dependências resolvidas; build viável no canal OBS escolhido e sem downloads ocultos.
- [ ] Serviço systemd não root, permissões CPU/GPU, configuração e ativação controlada testados.
- [ ] Modelo pequeno com licença/hash registrados; inferência CPU e CUDA reais, inclusive offline após importação.
- [ ] API mínima e streaming testados; autenticação, endpoints públicos, limites e erros documentados.
- [ ] Medir RAM/VRAM, latência e tokens/s com hardware, modelo, contexto e concorrência registrados; não anunciar desempenho só pelo sucesso do build.
- [ ] Falhas de modelo ausente/inválido, falta de memória/VRAM, porta ocupada, backend indisponível e cancelamento têm tratamento verificável.
- [ ] Reboot, atualização, remoção e recuperação preservam configurações/modelos e não exigem root para inferência.
- [ ] ISO Server padrão construída localmente e validada sem llama.cpp/dependências exclusivas.
- [ ] ISO Server com llama.cpp, CUDA e NVIDIA pré-instalados construída localmente e validada em hardware compatível, incluindo Secure Boot e atualização kernel/driver.
- [ ] Matriz cobre máquina/VM sem NVIDIA, hardware NVIDIA compatível e recuperação de falha; VMs e discos temporários são apagados ao concluir os testes.
- [ ] Documentação de ambas as imagens e dos RPMs contém instalação, modelos, recursos testados, limites, operação, diagnóstico e recuperação.
- [ ] Avaliar e especificar integração do Vega Web para llama.cpp, com divisão entre módulo/perfil, daemon e contratos, testes de autorização e empacotamento OBS; registrar decisão antes de implementá-la.
- [ ] Vega Web detecta NVIDIA e instalação do llama.cpp na máquina administrada e habilita os grupos NVIDIA/IA conforme a matriz; testar também ausência, falha de detecção, driver quebrado, serviço parado, atualização das capacidades e bloqueio de ações não autorizadas.
- [ ] Publicação dos RPMs no OBS e disponibilização das duas ISOs somente após os respectivos critérios de release; não presumir qualificação de ISO a partir do build do RPM.

Escopo desta issue: edição **Server**, com pacote CPU reutilizável e variante de ISO com **llama.cpp + NVIDIA**. Funcionalidades avançadas ficam registradas para avaliação e devem virar subtarefas quando adotadas, sem impedir a entrega inicial do fluxo de inferência e das duas imagens aprovadas.
