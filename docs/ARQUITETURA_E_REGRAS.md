# Arquitetura e regras de negócio

## Componentes

- **Frontend:** React 18, TypeScript, Vite e Lucide. A interface conversa exclusivamente com a API REST.
- **API:** FastAPI + Pydantic. Autenticação bearer JWT no modo de desenvolvimento.
- **Persistência:** SQLAlchemy 2.x, PostgreSQL, migrações Alembic. SQLite é permitido somente no modo local de desenvolvimento/teste.
- **Importação:** PyMuPDF para camada textual de PDF; Tesseract + Pillow para OCR de PDF escaneado e imagens; openpyxl para XLSX/XLSM.
- **Cálculo:** módulo `app/services/conciliacao/motor.py`, sem dependência da interface nem do banco.
- **Armazenamento:** os arquivos originais são salvos em diretório persistente por conciliação; o banco registra hash SHA-256 e metadados.

## Persistência e trilha

- `users`: usuário, e-mail, perfil e estado.
- `reconciliations`: identificação, banco, período, tolerância, responsável e estado do processamento.
- `import_files`: nome seguro, origem, caminho, SHA-256, estado, contagem e metadados da leitura.
- `transactions`: registros originais da fatura e do Odoo, incluindo valor assinado, natureza e JSON bruto.
- `match_results`: associação e classificação, regra, motivo, evidências, confiança, diferença e indicador manual.
- `audit_logs`: ator, ação, entidade, antes/depois, justificativa e data.

Há restrições únicas nos IDs de lançamento da fatura e Odoo em resultados, impedindo reutilização de uma mesma linha em mais de uma associação. Hash de arquivo impede importar o mesmo conteúdo mais de uma vez na mesma conciliação.

## Fluxo de importação

### Fatura PDF Itaú

O leitor percorre todas as páginas. Tenta texto nativo primeiro e OCR quando não existe conteúdo textual suficiente. Se não identificar lançamentos válidos, a importação recebe estado de falha e a API retorna erro; texto vazio não é considerado sucesso.

### Fatura Santander PNG/JPG

O original é preservado. O OCR usa orientação EXIF, escala mínima, autocontraste, ajuste de contraste e nitidez. Não solicita recorte manual. Os idiomas `por` e `eng` são usados quando instalados; em ambiente sem pacote português, o serviço tenta inglês e o pacote Docker instala ambos.

### Planilha Odoo

O importador procura a melhor linha de cabeçalho nas primeiras 40 linhas de todas as abas. Mapeia pelos nomes, aceita associação manual pelo rótulo exato do cabeçalho, calcula valor líquido a partir de débito/crédito quando necessário e informa linhas não reconhecidas e colunas desconhecidas. A extensão e a estrutura são validadas, sem confiar no nome do arquivo.

## Regras do motor

### Tipos e valores

Os valores são `Decimal`. O valor original é mantido para exibição e auditoria. Para comparar convenções de sinal entre bancos e Odoo, o serviço calcula um sinal econômico normalizado usando a natureza da transação: débito/compra como saída e crédito/estorno como entrada. A validação financeira deve confirmar se a classificação extraída corresponde ao layout real de cada emissor.

### Correspondência automática

1. Natureza da transação compatível.
2. Data dentro da tolerância configurada.
3. Valor equivalente dentro da tolerância monetária (zero por padrão).
4. Referência igual, ou evidência textual forte do estabelecimento/descrição.
5. Associação única e recíproca no grafo de candidatos.

A implementação não escolhe o primeiro candidato pela ordem do arquivo. Conflitos de um-para-muitos ou muitos-para-um não são resolvidos automaticamente.

### Divergência

Um candidato recíproco e identificável, com natureza e data compatíveis mas valor diferente, pode ser classificado como divergente. A diferença é exibida. Divergência nunca conta como conciliado.

### Pendente

Semelhança textual insuficiente, múltiplos candidatos ou evidência incompleta ficam pendentes. A interface apresenta o motivo e os candidatos quando identificados. O usuário precisa revisar e justificar qualquer alteração.

### Somente uma origem

Quando não há candidato admissível, o registro permanece em somente fatura ou somente Odoo. Isso não é uma falha do sistema nem deve ser corrigido artificialmente para inflar a conciliação.

### Associação e edição manual

A correção de origem é permitida antes do processamento e exige justificativa; fica registrada com os valores anteriores e novos. Depois do processamento, os dados de origem ficam bloqueados. A associação manual e o desfazimento exigem justificativa, checam unicidade, e geram auditoria.

## API principal

- `GET /api/health`
- `POST /api/auth/dev-login` (somente desenvolvimento)
- `GET /api/me`
- `POST /api/reconciliations`
- `POST /api/reconciliations/{id}/imports/invoice`
- `POST /api/imports/odoo/preview`
- `POST /api/reconciliations/{id}/imports/odoo`
- `PATCH /api/reconciliations/{id}/transactions/{transaction_id}`
- `POST /api/reconciliations/{id}/process`
- `GET /api/reconciliations` e `GET /api/reconciliations/{id}`
- `POST /api/reconciliations/{id}/matches/manual`
- `DELETE /api/reconciliations/{id}/matches/{match_id}`
- `GET /api/audit`
- `GET /api/reconciliations/{id}/export?format=xlsx|csv|pdf`

A documentação interativa é servida por `/docs` no FastAPI.
