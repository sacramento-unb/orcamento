# Orça

Aplicação local para acompanhar o orçamento mensal. O back-end Flask importa os
dados iniciais de `gastos mensais.ods`, armazena os lançamentos em SQLite e cria
uma nova versão `.xlsx` da planilha a cada alteração. O front-end React oferece
gráficos interativos, navegação de janeiro a dezembro, filtros e uma tela
completa de edição.

## O que foi importado

- Gastos fixos: Plano de saúde, Gasolina, Seguro carro, IPVA e Escola.
- Receitas fixas: Salário Enge — Líquido e Salário Digifarmz — Líquido.
- Os valores calculados da planilha original são importados como valores mensais.
- Os itens importados são repetidos nos 12 meses do ano.

O arquivo original não é modificado. O banco fica em `data/orcamento.db` e as
novas versões ficam em `exports/`. Cada arquivo exportado contém uma aba para
cada mês, além de `Visão geral` e `Lançamentos`.

Por segurança, planilhas, extratos, PDFs, bancos e exportações são arquivos
locais e não são enviados ao GitHub. Em um ambiente novo, a aplicação cria um
banco vazio. Para fazer a carga inicial no container, coloque a planilha como
`data/gastos mensais.ods` antes da primeira inicialização.

Na interface, **Novo gasto fixo** cria um valor recorrente a partir do mês
selecionado; **Gasto do mês** cria um lançamento pontual somente naquele mês.

### Importação bancária

Na tela `Lançamentos`, a opção **Importar do banco** aceita arquivos `.csv`,
`.ofx` e `.xlsx` exportados por aplicativos bancários. Antes de salvar, a
aplicação:

- mostra uma prévia dos gastos encontrados;
- identifica aplicações, aportes, resgates, rendimentos e posições de custódia
  sem tratá-los como gastos;
- permite selecionar transações e ajustar suas categorias;
- sugere conciliação com gastos fixos de descrição, categoria e valor semelhantes;
- ignora receitas quando o arquivo permite identificá-las;
- impede a importação duplicada da mesma transação;
- cria os gastos como lançamentos pontuais em seus meses de origem;
- gera uma nova versão da planilha após a confirmação.

Os investimentos importados ficam separados do orçamento na tela
**Investimentos**. Quando o arquivo informa ativo/produto, quantidade e preço
unitário, esses dados também são preservados. A planilha exportada possui uma
aba `Investimentos` exclusiva para essas movimentações.

Quando uma transação é conciliada, seu valor realizado substitui o valor
previsto do gasto fixo somente naquele mês. Nos outros meses, o valor fixo
continua inalterado. A prévia permite trocar a correspondência ou optar por
adicionar a transação separadamente. Excluir o lançamento bancário restaura
automaticamente o valor fixo daquele mês.

## Executar em desenvolvimento

Requer Python 3.11+ e Node.js 18+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend
npm install
npm run dev
```

Em outro terminal, a partir da raiz do projeto:

```bash
source .venv/bin/activate
python -m backend.app
```

Abra `http://localhost:5173`.

Para executar os testes em uma instalação nova:

```bash
pip install -r backend/requirements-dev.txt
pytest
```

## Executar

```bash
cd frontend
npm run build
cd ..
./start.sh
```

O script inicia o Flask pelo servidor WSGI Gunicorn, com dois workers e quatro
threads por worker. Flask entrega a interface e a API em
`http://localhost:5000`.

As opções podem ser ajustadas por variáveis de ambiente:

```bash
WEB_CONCURRENCY=3 GUNICORN_THREADS=4 GUNICORN_TIMEOUT=180 ./start.sh
```

## Testes

```bash
source .venv/bin/activate
pytest
```

## Executar com Docker

O container utiliza um build multi-stage: Node compila o React e a imagem final
contém apenas Python, Flask e Gunicorn. O banco, as exportações e a planilha
original permanecem no computador por meio de bind mounts.

```bash
docker compose up --build -d
```

A aplicação fica disponível em `http://localhost:5000`.

Comandos úteis:

```bash
# Ver estado e health check
docker compose ps

# Acompanhar logs
docker compose logs -f app

# Recriar após alterações no código
docker compose up --build -d

# Parar sem apagar banco ou exportações
docker compose down
```

Os diretórios persistentes continuam sendo `data/` e `exports/`. O comando
`docker compose down` não apaga esses arquivos. Antes de um backup manual, pare
o serviço e copie ambos os diretórios:

```bash
docker compose stop
tar -czf orca-backup.tar.gz data exports
docker compose start
```

Para mudar a porta externa:

```bash
APP_PORT=8080 docker compose up -d
```

## CI/CD

Alterações enviadas à branch `main` passam pelos testes do back-end e pela
compilação do front-end no GitHub Actions. Depois da validação, um runner
auto-hospedado com o rótulo `orcamento-production` executa o deploy no servidor.
O conteúdo versionado é sincronizado em `~/apps/orcamento`, preservando o banco,
as exportações e o `.env`, e o Docker Compose recria somente o necessário.

No servidor, o container fica restrito a `127.0.0.1:5050`; o Nginx publica o
serviço como `http://orcamento.local` na porta 80. O estado do pipeline aparece
na aba **Actions** do repositório.

## API principal

- `GET /api/summary?month=AAAA-MM`
- `GET /api/entries`
- `GET /api/investments?year=AAAA`
- `POST /api/entries`
- `PUT /api/entries/:id`
- `DELETE /api/entries/:id`
- `POST /api/export`
- `GET /api/exports`
