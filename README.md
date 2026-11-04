# Grupo EPA — Sistema Web de Conciliação Bancária

Aplicação web em React + TypeScript, API FastAPI, SQLAlchemy/Alembic e PostgreSQL. A aplicação importa faturas Itaú em PDF, faturas Santander em PNG/JPG e arquivos Odoo em XLSX/XLSM; permite revisar os dados extraídos antes de executar o motor; apresenta resultados explicáveis; mantém auditoria e exporta relatórios.

> **Estado desta entrega:** versão integrada para desenvolvimento e homologação técnica. Não está liberada para produção. O login Microsoft Entra ID, hospedagem corporativa, gestão de segredos e validação com os arquivos reais da empresa dependem da TI e da homologação financeira.

## 1. Funcionalidades disponíveis

- Dashboard financeiro alimentado pelos dados efetivamente importados. Sem importações, os indicadores permanecem zerados; não há dados de demonstração.
- Identidade visual do Grupo EPA e arquivo de logo separado em `frontend/public/epa-logo.png`.
<<<<<<< HEAD
- Cadastro de conciliações por banco e período, com tolerância de data configurável (0 a 60 dias; padrão de 3 dias).
- Importação de fatura Itaú em PDF, leitura de texto em todas as páginas e OCR nas páginas escaneadas/sem texto útil.
- Importação de fatura Santander em PNG/JPG, com correção de orientação EXIF, escala, contraste e nitidez antes do OCR. O arquivo original é preservado.
- Prévia dos lançamentos e possibilidade de corrigir campos antes do processamento, com justificativa e trilha de auditoria.
- Importação Odoo XLSX/XLSM por nomes de cabeçalho, busca da linha de cabeçalho nas primeiras 40 linhas, sugestão e mapeamento manual de campos, inclusive natureza/tipo. Quando existirem colunas Débito e Crédito, elas prevalecem sobre um Total genérico; quando só houver Valor/Total sem natureza explícita, o sistema marca a natureza como indefinida e exige revisão, em vez de presumir crédito. Colunas desconhecidas são informadas e preservadas no dado bruto.
=======
- Cadastro de conciliações por banco e período, com tolerância de data configurável (0 a 31 dias; padrão de 3 dias).
- Importação de fatura Itaú em PDF, leitura de texto em todas as páginas e OCR nas páginas escaneadas/sem texto útil.
- Importação de fatura Santander em PNG/JPG, com correção de orientação EXIF, escala, contraste e nitidez antes do OCR. O arquivo original é preservado.
- Prévia dos lançamentos e possibilidade de corrigir campos antes do processamento, com justificativa e trilha de auditoria.
- Importação Odoo XLSX/XLSM por nomes de cabeçalho, busca da linha de cabeçalho nas primeiras 40 linhas, sugestão e mapeamento manual de campos. Colunas desconhecidas são informadas e preservadas no dado bruto.
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
- Motor independente da interface, com `Decimal`, comparação de valor, data, natureza da transação, nome/referência, confiança e explicação.
- Resultados: conciliado, divergente, somente Odoo, somente fatura e pendente de revisão.
- Associação manual e desfazimento com justificativa e auditoria.
- Histórico, auditoria e exportação XLSX, CSV e PDF.
- PostgreSQL em Docker Compose e migração inicial Alembic.

## 2. Regras centrais do motor

1. Valor é obrigatório para conciliação automática. A tolerância monetária padrão é zero.
2. A data deve estar dentro da tolerância definida na conciliação.
3. A natureza (débito/compra ou crédito/estorno) precisa ser compatível. A comparação financeira normaliza convenções de sinal entre banco e Odoo, mas mantém o valor original guardado e exibido.
4. A referência pode identificar a contraparte; sem referência, o nome/descrição precisa oferecer evidência textual forte.
5. A conciliação automática exige correspondência única nos dois sentidos. O mesmo lançamento não pode ser usado duas vezes.
6. Similaridade textual fraca ou múltiplos candidatos geram pendência, não conciliação automática.
7. Uma contraparte confiável com valor diferente fica divergente, nunca conciliada.
8. Casos sem evidência suficiente ficam pendentes ou somente de uma origem.
9. Cada decisão guarda regra, motivo, evidências, diferença e confiança.
10. Nenhum agrupamento de várias linhas é feito automaticamente nesta versão.

A tolerância padrão histórica de 1 dia identificada na macro anterior não foi fixada. A nova configuração começa em até 3 dias, conforme a especificação mais recente, e pode ser ajustada por conciliação. A homologação deve definir os limites efetivos por banco e tipo de transação.

## 3. Requisitos

### Execução integrada com Docker

- Docker Desktop (ou Docker Engine) com Docker Compose.
- Acesso à internet na primeira construção das imagens para baixar imagens base e dependências.

### Execução local sem Docker

- Python 3.12.
- Node.js 22 ou compatível com Vite 6.
- Tesseract OCR instalado e configurado. Recomenda-se instalar os idiomas `por` e `eng`.
- PostgreSQL, ou SQLite apenas para desenvolvimento/testes locais.

## 4. Configuração e inicialização com Docker

No terminal, a partir desta pasta:

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Edite `.env` e substitua obrigatoriamente `POSTGRES_PASSWORD` e `SECRET_KEY` por segredos fortes e exclusivos. Para gerar um segredo aleatório com Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Execute:

```powershell
docker compose up --build -d
docker compose ps
```

Acesse:

- Interface: http://localhost:5173
- API: http://localhost:8000
- Documentação interativa da API: http://localhost:8000/docs
- Verificação da API: http://localhost:8000/api/health

Para encerrar:

```powershell
docker compose down
```

Os dados do PostgreSQL e os arquivos importados são mantidos nos volumes Docker `postgres_data` e `uploads`. **Não execute `docker compose down -v` em um ambiente com dados que devam ser preservados**, pois isso remove os volumes.

A tela de login nesta versão é identificada como **desenvolvimento**. Use a conta de demonstração pré-preenchida apenas no ambiente local. O endpoint de login de desenvolvimento deve permanecer desabilitado na implantação corporativa.

## 5. Execução local para desenvolvimento

### Backend

```bash
cd backend
python -m venv .venv
```

Ative o ambiente virtual e instale as dependências:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
```

Defina `DATABASE_URL=sqlite:///./epa_dev.db` e `ENVIRONMENT=development`, ou use as variáveis equivalentes no arquivo `.env`. Com o Tesseract configurado:

```bash
uvicorn app.main:app --reload --port 8000
```

A API cria as tabelas automaticamente apenas no modo de desenvolvimento com SQLite. Para PostgreSQL, a migração Alembic é o fluxo esperado:

```bash
alembic upgrade head
```

### Frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

<<<<<<< HEAD
Acesse http://localhost:5173. No modo Vite, as chamadas `/api` são encaminhadas pelo proxy para `http://127.0.0.1:8000`. No Docker, o Nginx encaminha `/api` ao serviço backend, sem fixar `localhost` no navegador. Para uma API em outro endereço, configure `VITE_API_URL` no build.
=======
Acesse http://localhost:5173. O endereço padrão da API é `http://localhost:8000/api`; pode ser alterado pela variável `VITE_API_URL` no build.
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f

## 6. Testes do backend

Com as dependências instaladas, na pasta `backend`:

```bash
PYTHONPATH=. pytest -q
```

<<<<<<< HEAD
A suíte cobre normalização monetária/data, motor de conciliação, importação PDF multipágina, mapeamento Odoo (incluindo sinais e natureza), OCR de imagem, API integrada, auditoria, ajustes, reprocessamento e exportação. Consulte `docs/VALIDACAO_E_LIMITACOES.md` para os resultados executados nesta entrega e para o que ainda não foi homologado.
=======
A suíte cobre normalização monetária/data, motor de conciliação, importação PDF multipágina, mapeamento Odoo, OCR de imagem, API integrada, auditoria, ajustes, reprocessamento e exportação. Consulte `docs/VALIDACAO_E_LIMITACOES.md` para os resultados executados nesta entrega e para o que ainda não foi homologado.
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f

## 7. Fluxo operacional recomendado

1. Criar uma nova conciliação e escolher o banco, o período e a tolerância.
2. Importar a fatura (PDF Itaú ou imagem Santander).
3. Importar a planilha Odoo e revisar o mapeamento sugerido.
4. Conferir as duas prévias, os nomes, as datas, os sinais e os valores. Corrigir dados incorretos com justificativa.
5. Executar a conciliação.
6. Revisar pendências e divergências. Uma associação manual requer justificativa.
7. Exportar o resultado depois da conferência.

Não use resultados de demonstração ou uma contagem histórica como expectativa fixa. Compare os resultados com a documentação original e com a validação financeira responsável.

## 8. Estrutura

```text
grupo-epa-conciliacao/
├── backend/
│   ├── app/api/                 # Endpoints REST
│   ├── app/core/                # Configuração e autenticação
│   ├── app/db/                  # Sessões e base SQLAlchemy
│   ├── app/models/              # Entidades persistentes
│   ├── app/schemas/             # Contratos Pydantic
│   ├── app/services/
│   │   ├── conciliacao/         # Motor financeiro independente
│   │   ├── importacao/           # PDF/imagem e Odoo
│   │   └── normalizacao.py      # Datas, textos e Decimal
│   ├── alembic/                 # Migrações
│   └── tests/                   # Testes automatizados
├── frontend/
│   ├── public/epa-logo.png      # Logo do Grupo EPA
│   └── src/                     # React, páginas e dashboard
├── docs/                        # Arquitetura, regras e validação
├── docker-compose.yml
└── .env.example
```

## 9. Segurança e produção

Antes de qualquer uso real, a TI deve implementar e validar no mínimo:

- Microsoft Entra ID / OIDC real no frontend e validação de tokens no backend; o endpoint `dev-login` não é autenticação corporativa.
- Perfis e escopo corporativo definitivos, incluindo segregação por empresa/estabelecimento e administração de usuários.
- Segredos no cofre corporativo (por exemplo, Azure Key Vault), TLS, política de sessão, rotação de chaves e CORS restrito aos domínios aprovados.
- Hospedagem aprovada, backup/restauração testados, retenção e descarte de arquivos, monitoramento, logs protegidos e plano de continuidade.
- Revisão de segurança, testes de carga/concorrência e homologação com amostras reais (anonimizadas quando necessário) de todas as variações Itaú, Santander e Odoo.
- Aprovação financeira dos critérios de estorno, crédito, débitos, tolerância de data, duplicidades e divergências.

A aplicação deliberadamente não declara prontidão para produção. As limitações conhecidas estão em `docs/VALIDACAO_E_LIMITACOES.md`.
