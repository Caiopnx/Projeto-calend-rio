# Feriados de Volta Redonda / RJ — versão 1.1

O aplicativo calcula localmente 15 feriados recorrentes para o ano selecionado. Não acessa a internet. A lista representa o calendário civil atual projetado nos anos escolhidos; não é uma reconstrução da legislação vigente em cada ano histórico.

## Regras incluídas

- Nacionais: 01/01, Paixão de Cristo (Páscoa menos dois dias), 21/04, 01/05, 07/09, 12/10, 02/11, 15/11, 20/11 e 25/12.
- Estaduais do Rio de Janeiro: terça-feira de Carnaval (Páscoa menos 47 dias) e São Jorge (23/04).
- Municipais de Volta Redonda: Corpus Christi (Páscoa mais 60 dias), Santo Antônio (13/06) e Aniversário de Volta Redonda (17/07).

A Páscoa é calculada pelo computus gregoriano. A Páscoa em si não é cadastrada como feriado adicional. Segunda-feira de Carnaval, Quarta-feira de Cinzas, emendas, datas comemorativas, Dia do Servidor e feriados exclusivos da capital não entram automaticamente.

Paixão de Cristo foi mantida na categoria **Nacional**, conforme a organização administrativa solicitada para este aplicativo. Sua base de feriado religioso em Volta Redonda também consta da legislação municipal citada abaixo. Não é necessário cadastrá-la novamente como municipal.

São Jorge permanece em 23/04, conforme solicitado. Compensações e transferências de expediente de repartições públicas não são aplicadas automaticamente ao calendário civil. A tela Feriados permite ajustar a ocorrência do ano caso o setor precise registrar uma transferência específica.

## Gerenciamento

Na tela **Feriados**, selecione o ano e clique em Aplicar. O filtro permite Todos, Nacional, Estadual e Municipal. A tabela apresenta data, nome, tipo e origem.

- **Adicionar feriado:** cria uma data específica no ano selecionado.
- **Editar neste ano:** em um padrão, cria uma exceção anual. O cadastro recorrente continua intacto. Em um personalizado, edita o registro específico.
- **Remover neste ano:** oculta apenas a ocorrência selecionada de um padrão, ou exclui o personalizado selecionado. Exige confirmação.
- **Restaurar padrões do ano:** desfaz edições e remoções de padrões desse ano. Mantém feriados personalizados e ajustes de outros anos.

No calendário, números vermelhos e em negrito identificam os feriados. As barras coloridas continuam representando férias. Clique no dia para ver os nomes dos feriados e as pessoas de férias.

## Arquivo feriados.json

O arquivo separado contém `versao`, `feriados`, `personalizados` e `excecoes`. As regras fixas possuem `id`, `nome`, `tipo`, `dia`, `mes` e `movel: false`. As móveis possuem `referencia: "pascoa"`, `deslocamento` em dias e `movel: true`.

As exceções referenciam `origem_id` e `ano`; usam `removido: true` para ocultar ou guardam a nova data, nome e tipo. Não sobrescrevem a lista de regras. Novas regras recorrentes podem ser acrescentadas futuramente por manutenção desse arquivo, com IDs únicos e os mesmos campos, mantendo o aplicativo fechado e um backup prévio. Para a administração diária, use a tela do aplicativo.

## Fontes oficiais consultadas em 10/09/2026

- [Lei estadual 5.243/2008 — terça-feira de Carnaval](https://alerjln1.alerj.rj.gov.br/contlei.nsf/b24a2da5a077847c032564f4005d4bf2/063f7c027766eab48325744a007a4ab0).
- [Lei municipal 3.530/1999 — Corpus Christi, 17 de julho e Sexta-feira da Paixão](https://sapl.voltaredonda.rj.leg.br/norma/3551).
- [Lei municipal 5.484/2018 — Santo Antônio em Volta Redonda](https://sapl.voltaredonda.rj.leg.br/norma/4025).
- [Lei federal 14.759/2023 — 20 de novembro](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2023/lei/l14759.htm).
- [Calendário administrativo municipal de 2026, publicado no VR em Destaque](https://www.voltaredonda.rj.gov.br/images/Documentos/VRDestaques/2024/2025-12-29_2273-extra.pdf). O documento distingue feriados, compensações e expediente. O aplicativo não incorpora automaticamente suas emendas e transferências administrativas.

Futuras alterações legais precisam ser revisadas pelo responsável pelo calendário e registradas no aplicativo; não há atualização pela internet.
