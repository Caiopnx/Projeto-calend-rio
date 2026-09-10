# Calendário de Férias STMU

> Este repositório contém o código-fonte da versão 1.1. O executável e os dados administrativos não são versionados. Depois de clonar, use `preparar.bat` e `iniciar.bat` para executar pelo código, ou `gerar_exe.bat` para criar `dist\CalendarioFeriasSTMU.exe`.

Aplicativo desktop Windows, em Python, com interface Tkinter/ttk. Funciona offline: os cadastros e configurações são armazenados exclusivamente em arquivos JSON. Não utiliza banco de dados, APIs ou serviços externos.

## Abrir agora: EXE já gerado

Abra `iniciar.bat` ou `dist\CalendarioFeriasSTMU.exe`. O executável Windows de 64 bits não exige Python ou bibliotecas no computador de destino. A versão 1.1 mantém o projeto existente e os cadastros salvos; uma instalação nova começa vazia.

Foram aprovados 23 testes automatizados de serviços, incluindo os 12 anteriores. O autoteste também cobre os formulários, períodos de 10 + 20, filtro de feriados, feriado junto com férias, nome do setor, prévia A4, backup e reabertura. A impressão física precisa ser conferida com o leitor de PDF e a impressora do computador de destino.

## Novidades da versão 1.1

- Períodos de **30 dias**, **15 + 15 dias** e **10 + 20 dias**, mantendo contagem inclusiva e bloqueio de sobreposição. Em 10 + 20, o primeiro período deve ter 10 dias e o segundo 20.
- Tela **Feriados**, com ano, filtros por tipo, inclusão manual, edição e remoção por ano, e restauração dos padrões. São incluídos feriados nacionais, estaduais do RJ e municipais de Volta Redonda, com datas móveis calculadas offline. Veja os critérios e fontes em `FERIADOS.md`.
- Números de feriados em vermelho e negrito, sem esconder as barras de férias, nas visões anual/mensal, na prévia e no PDF.
- Em **Dados e backup → DADOS DO CALENDÁRIO**, informe o nome do setor e a sigla opcional. Clique em Salvar dados do calendário. O nome aparece no calendário e nos documentos; a sigla identifica o cabeçalho do aplicativo.
- `feriados.json` separado dos demais dados, incluído no backup e na restauração.

Na primeira abertura da nova versão com dados antigos, o aplicativo guarda uma cópia dos JSON originais em `backups/antes_atualizacao_...`, ao lado de `data`, e acrescenta as novas configurações e o arquivo de feriados. Não é necessário recadastrar funcionários nem férias. Se restaurar um backup antigo de três JSON, os feriados e o nome/sigla atuais são preservados quando esses campos não existiam no backup. Backups novos precisam conter os quatro arquivos.

## Executar pelo código

No computador de desenvolvimento, instale Python 3.12 ou posterior com pip e Tcl/Tk. Execute `preparar.bat` uma vez e depois `iniciar.bat`. A preparação instala ReportLab, Pillow e PDFium; o aplicativo não utiliza a internet durante o funcionamento.

Alternativamente, na pasta do projeto:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Para preparar sem internet, leve uma pasta `wheels` com as dependências compatíveis com a versão de Python e Windows do computador e instale com `pip install --no-index --find-links wheels -r requirements.txt`.

## Uso

1. **Funcionários:** informe nome, matrícula única, setor, cargo, cor e situação. A pesquisa cobre esses campos. Selecione uma linha para editar, excluir ou alterar a cor. A exclusão exige confirmação e remove as férias vinculadas. Funcionários inativos permanecem no histórico e no calendário, mas não aparecem para novas solicitações.
2. **Férias:** escolha 30 dias consecutivos, 15 + 15 dias ou 10 + 20 dias. Digite datas no formato DD/MM/AAAA. “Calcular data final” preenche o fim a partir do início. A contagem inclui o primeiro e o último dia, inclusive feriados. Salvar valida duração, datas e sobreposição para a mesma pessoa. Editar/excluir atua na solicitação inteira, incluindo os dois períodos quando fracionada.
3. **Calendário:** escolha um ano de 1 a 9999 e clique em Aplicar, ou pressione Enter. A visão anual tem os 12 meses; o seletor permite ver um mês. Clique no nome de um mês para ampliá-lo. Clique em um dia para consultar todos os funcionários de férias. As faixas coloridas exibem ausências simultâneas; a legenda inclui apenas pessoas com férias no ano escolhido. Férias que atravessam o ano aparecem nos dois anos.
4. **Impressão:** a prévia exibe o PDF final rasterizado, com proporção A4, margens, orientação retrato/paisagem, zoom e navegação de páginas. O calendário ocupa a primeira página. Legendas longas continuam em páginas extras, com nomes quebrados em linhas. Gerar PDF permite escolher o destino.
5. **Imprimir:** usa o comando de impressão do leitor de PDF padrão do Windows. É necessário um leitor com associação de impressão e uma impressora configurada. Confira A4 e a orientação no leitor. Se o leitor não aceitar impressão automática, salve o PDF, abra-o e use Ctrl+P. O aplicativo informa o envio do comando, sem afirmar que a impressão física foi concluída. Cópias encaminhadas ao leitor ficam na pasta `impressao`, ao lado de `data`.
6. **Dados e backup:** Fazer backup copia os quatro JSON para uma pasta datada. Restaurar backup solicita a pasta do backup, valida os registros e pede confirmação. Antes de substituir, salva os dados anteriores em `backups`, ao lado de `data`. Backups da versão anterior também são aceitos.

## Onde ficam os dados

- Executando o código: pasta `data` na raiz do projeto, criada na primeira abertura.
- EXE instalado: `%LOCALAPPDATA%\STMU\CalendarioFerias\data`. Assim a aplicação não precisa gravar em Program Files nem pedir acesso de administrador. Cada usuário Windows tem seus próprios dados.
- EXE portátil: crie um arquivo vazio `portable.flag` ao lado do EXE. Os JSON ficam na pasta `data` ao lado dele. Use uma pasta com permissão de escrita.
- Também é possível configurar a variável `STMU_DATA_DIR` com o caminho de uma pasta local.

Arquivos principais: `funcionarios.json`, `ferias.json`, `configuracoes.json` e `feriados.json`. Os períodos têm IDs automáticos e um identificador `solicitacao` para manter juntos os pares 15 + 15 e 10 + 20. Os exemplos simplificados sem esse identificador precisam ser adaptados antes de serem importados.

As gravações usam arquivo temporário, sincronização e substituição atômica. `transacao.json` permite completar uma gravação interrompida na abertura seguinte. `.stmu.lock` bloqueia duas instâncias gravando a mesma pasta. Não apague esses arquivos com o aplicativo aberto. Em caso de erro de gravação, reabra antes de continuar. Dados inválidos não são sobrescritos silenciosamente. Se os dados impedirem a inicialização, feche o aplicativo, preserve a pasta inteira e copie os quatro JSON de um backup válido para `data`. Um `transacao.json` existente pertence à recuperação: preserve-o junto com a pasta antiga antes de restaurar manualmente.

Os arquivos JSON não são criptografados; controle o acesso à pasta e guarde backups periódicos. A recuperação de gravação não substitui uma cópia em outro dispositivo. O aplicativo é de uso local, não sincroniza computadores. Ao transportar os dados, use backup/restauração ou copie a pasta `data` inteira com o aplicativo fechado.

## Gerar CalendarioFeriasSTMU.exe

Execute `gerar_exe.bat` em Windows. Ele instala as dependências de compilação, executa os testes e gera `dist\CalendarioFeriasSTMU.exe` com PyInstaller. Não inclui os cadastros do desenvolvedor no executável.

Comandos equivalentes:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm CalendarioFeriasSTMU.spec
```

O computador de destino não precisa de Python nem de internet. O EXE contém Python, Tkinter e bibliotecas de geração/prévia de PDF. Teste o executável no Windows de destino antes da distribuição. Compilações sem assinatura digital podem apresentar avisos do Windows.

## Instalador Windows

Depois de gerar o EXE, abra `installer\STMU.iss` no Inno Setup 6 e compile. A saída será `dist\InstaladorCalendarioFeriasSTMU.exe`, com assistente em português, atalhos e desinstalação. Instala por usuário, sem administrador. A desinstalação não remove os dados administrativos em LocalAppData.

O script do instalador está preparado; o instalador não foi compilado neste ambiente, que não dispõe do Inno Setup. O EXE já pode ser utilizado diretamente.

## Estrutura e testes

- `app/main.py`: inicialização, navegação, tema e tratamento de erros.
- `app/ui/`: calendário, funcionários, férias, impressão e backup.
- `app/services/`: JSON, validação, calendário real, backup/restauração e ReportLab.
- `tests/test_services.py`: persistência, duração, sobreposição, datas, backup, recuperação, bloqueio e PDF multipágina.
- `tests/test_updates.py`: 10 + 20, migração, backups antigos e novos, feriados, ajustes por ano e PDF com título longo.
- `CalendarioFeriasSTMU.spec`: empacotamento Windows.

Não existe limitação automática de quantidade de solicitações por ano nem análise trabalhista de saldo/direito adquirido: cada solicitação é validada por duração e sobreposição. Setor e cargo são campos livres.

As versões exatas usadas na compilação estão em `requirements-tested.txt`. Para diagnóstico local, execute o EXE com `--autoteste` seguido de uma pasta de saída. O autoteste usa apenas cadastros temporários e grava `autoteste.json` nessa pasta, sem modificar os dados administrativos.
