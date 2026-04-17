# CLAUDE.md local do projeto

Este arquivo complementa o CLAUDE.md global e define regras permanentes para a raiz
do repositório.

## Precedência local
- Siga nesta ordem: prompt explícito do usuário, este `CLAUDE.md` local e o
  CLAUDE.md global.
- Quando duas regras parecerem compatíveis, aplique a mais específica.
- Quando houver conflito entre regras válidas, aplique a mais restritiva.

## Contexto do repositório
- Sempre valide se existe `PROJECT_CONTEXT.md` na raiz do projeto aberto.
- Se `PROJECT_CONTEXT.md` existir e o escopo permitir, leia esse arquivo no
  início da primeira solicitação relevante antes de planejar ou editar.
- Volte a consultar `PROJECT_CONTEXT.md` quando a conversa se alongar, quando o
  contexto estiver insuficiente ou quando a alteração mexer em arquitetura,
  estrutura, entrypoints, integrações, variáveis de ambiente, ambiente Python ou
  fluxo operacional.
- Se `PROJECT_CONTEXT.md` não existir, siga com o contexto confirmado nos
  arquivos visíveis e na working tree atual. Não crie esse arquivo por iniciativa
  própria, salvo pedido explícito do usuário.
- Quando `PROJECT_CONTEXT.md` tiver uma seção dedicada de ambiente Python, reuse
  esse ambiente como referência padrão para validações enquanto ele continuar
  coerente com o projeto.

## Escopo de trabalho
- Se o prompt restringir leitura ou alteração a arquivos específicos, mantenha-se
  estritamente dentro desse escopo.
- Se o prompt não restringir o escopo, propague alterações necessárias para
  imports, assinaturas, consumidores, módulos, arquivos relacionados e referências
  operacionais que precisem ser atualizadas para manter o projeto consistente.
- Não crie aliases, wrappers de compatibilidade ou parâmetros obsoletos apenas
  para evitar atualizar consumidores.
- Se uma propagação necessária atingir arquivo explicitamente fora do escopo
  autorizado, não expanda a alteração silenciosamente; reporte o bloqueio.

## Estrutura, arquivos novos e documentação
- Preserve a arquitetura e os entrypoints atuais do projeto, salvo quando o
  prompt pedir refatoração estrutural.
- Ao criar arquivos ou pastas, siga o padrão de nomenclatura do diretório de
  destino.
- Se a pasta de destino usar módulos Python no padrão `_xx_nome.py`, use a
  próxima numeração após a maior existente. Se não usar esse padrão, crie o novo
  arquivo sem numeração.
- Não crie artefatos temporários, documentação auxiliar ou camadas intermediárias
  sem necessidade real do trabalho solicitado.
- Não altere nem apague `CLAUDE.md` por iniciativa própria.

## Consistência do projeto
- Preserve contratos públicos, integração com deploy, scripts de entrada,
  arquivos de runtime e manifests do projeto, salvo instrução explícita em
  contrário.
- Em prompts de finalização estrutural, higienização pronta para Git ou remoção
  de legado, trate resíduos transitórios, caches, artefatos de teste, saídas
  temporárias, notebooks de experimento e estruturas antigas sem uso real como
  candidatos prioritários à eliminação, migração ou consolidação.
- Sempre que editar arquivos, reavalie se `PROJECT_CONTEXT.md`, `README.md`,
  manifests de dependência ou documentação operacional ficaram desatualizados
  pelo escopo permitido e atualize o que for necessário.
- Se a alteração mudar algo já documentado em `PROJECT_CONTEXT.md`, atualize esse
  arquivo no mesmo trabalho.

## Validação local
- Após alterar código ou arquivos operacionais, execute as validações necessárias
  conforme o CLAUDE.md global.
- Quando o projeto depender de Docker ou WSL para validar corretamente, use-os
  quando forem relevantes e trate artefatos, containers e imagens de validação
  conforme a política global.
- Quando testes caros gerarem saídas relevantes, salve esses artefatos em
  `tests/artefatos_testes/`.

## Resposta final
- Mantenha a resposta final curta e direta.
- Informe apenas status da implementação, validações executadas e bloqueio
  técnico relevante, quando existirem.
