# Relatório de validação e limitações conhecidas

## Execução realizada nesta entrega

| Verificação | Resultado | Observação |
|---|---|---|
| Pytest backend | **24 aprovados** | Normalização, motor, importação, OCR, endpoints, ajuste manual, auditoria, reprocessamento e exportação. |
| Migração Alembic | **Aprovada** | Executada em SQLite descartável; 7 tabelas criadas e coluna `is_manual` verificada na tabela `match_results`. |
| OCR imagem Santander | **Aprovado em amostra sintética** | Dois lançamentos de teste foram extraídos de PNG gerado para teste. Não equivale a homologação com fatura original. |
| Sintaxe TypeScript/TSX | **Verificada** | 4 arquivos `.ts`/`.tsx` passaram pela transpilation sintática com TypeScript global. Isso não substitui a checagem completa de tipos. |
| Build completo Vite | **Não executado** | A instalação de dependências do frontend excedeu o limite de rede disponível nesta sessão. Executar `npm install` e `npm run build` no ambiente de desenvolvimento. |
| Docker Compose / PostgreSQL em contêiner | **Não executado nesta sessão** | Arquivos de implantação preparados, mas a subida dos serviços não foi validada aqui. |
| Login Microsoft Entra ID | **Pendente** | Integração corporativa necessita registro de aplicação, tenant, fluxo OIDC e validação de token com a TI. |
| Homologação com arquivos reais | **Pendente** | Necessária para validar todos os layouts e a extração financeira. |

Comando de teste utilizado:

```bash
cd backend
PYTHONPATH=. pytest -q
```

Resultado observado: `24 passed`.

## Limitações funcionais conhecidas

1. **Entra ID:** a tela e endpoint de login desta versão são de desenvolvimento. Não usar login demonstrativo na empresa nem expor o endpoint em produção. A autenticação corporativa OIDC/Entra ainda precisa ser desenvolvida e validada.
2. **Homologação de OCR:** a extração foi testada com uma imagem sintética e um PDF textual multipágina. Ainda faltam faturas reais Itaú/Santander, incluindo digitalizações inclinadas, baixa resolução, páginas com colunas paralelas, créditos, estornos e layouts distintos. O OCR genérico pode precisar de parser específico por banco.
3. **OCR de PDF escaneado:** está implementado por página, mas precisa ser homologado com PDFs escaneados reais e diferentes resoluções. A disponibilidade dos idiomas depende do Tesseract no ambiente; o Docker instala português e inglês.
4. **Detecção de sinal/natureza:** heurísticas de texto, valor e cabeçalho inferem débito/crédito. A regra final deve ser validada com os layouts bancários e os campos usados pelo Grupo EPA para evitar confusão entre compra, crédito, estorno e ajuste.
5. **Agrupamento de lançamentos:** o motor não executa conciliação automática um-para-vários ou vários-para-um. Esses casos permanecem para revisão. A associação manual atual é um-para-um.
6. **Formatos Odoo:** são aceitos XLSX/XLSM. CSV ainda não está implementado. Cabeçalhos e colunas desconhecidos são preservados/informados, mas podem exigir mapeamento e novas regras para exportações Odoo específicas.
7. **Processamento síncrono:** importação/OCR é síncrona na requisição. Uma fila de tarefas e acompanhamento de progresso são recomendados para faturas grandes ou processamento simultâneo.
8. **Permissões organizacionais:** há controle por perfil básico e propriedade da conciliação; o modelo completo de segregação por empresa, filial/estabelecimento, grupos do Entra e administração de contas ainda depende do desenho de TI.
9. **Exportação PDF:** relatório básico em página paisagem; precisa ser revisado visualmente com volumes grandes e nomes muito extensos antes do uso corporativo.
10. **Infraestrutura:** backups, restore, retenção, antivírus/inspeção de arquivos, Key Vault, TLS, WAF, monitoramento, política de logs, limite corporativo de upload e continuidade não foram validados em ambiente Azure.
11. **Build frontend e containers:** não foram executados nesta sessão por restrição de instalação de dependências/rede. Execute a compilação e o Docker Compose na rede de desenvolvimento antes de homologar.

## Critérios para homologação financeira

- Fornecer amostras representativas e, quando possível, anonimizadas de cada layout Itaú, Santander e Odoo.
- Definir regra de sinal para compra, débito, crédito, estorno, anuidade e ajuste.
- Confirmar tolerância de data por banco, modalidade e operação; o padrão de 3 dias é parametrizável, não uma regra universal validada.
- Comparar cada lançamento com o documento original e registrar casos esperados e casos proibidos.
- Validar totais brutos e líquidos por fonte, quantidade por status e diferença financeira.
- Exercitar reprocessamento, duplicidade, concorrência e importação repetida com usuários distintos.
- Aprovar manualmente a lista de pendências e divergências antes de liberar qualquer processo produtivo.

**Conclusão:** o backend possui 24 testes automatizados aprovados e a migração está verificada. A análise sintática TS/TSX também foi executada. A aplicação é uma base funcional de desenvolvimento/homologação, mas build do frontend, subida Docker, autenticação corporativa e homologação com documentos reais continuam pendentes. Não está pronta para produção.
