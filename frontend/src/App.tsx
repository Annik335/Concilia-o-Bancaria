import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import {
  Activity, AlertCircle, ArrowLeft, CheckCircle2, Clock3, Download, FileSpreadsheet,
  FileText, History, LayoutDashboard, ListChecks, LogOut, Plus, RefreshCw, ShieldCheck,
  UploadCloud, Wallet, X, Pencil, Search, LockKeyhole,
} from 'lucide-react';
import { api, clearToken, getApiError, getToken, type AuditRecord, type OdooPreview } from './services/api';
import type { MatchResult, Reconciliation, ReconciliationDetail, Summary, Transaction } from './types';
// Ajuste temporário para rodar sem Docker localmente
if (typeof (window as any).getToken === 'undefined') {
  (window as any).getToken = () => {
    console.log("getToken chamada localmente (Mock)");
    return localStorage.getItem('token') || '';
  };
}

type UserProfile = { id: number; email: string; name: string; role: string };
type Page = 'dashboard' | 'new' | 'detail' | 'history' | 'audit';
type ResultTab = 'TODOS' | 'CONCILIADO' | 'DIVERGENTE' | 'PENDENTE_REVISAO' | 'SOMENTE_ODOO' | 'SOMENTE_FATURA';

const ZERO_SUMMARY: Summary = {
  CONCILIADO: 0, DIVERGENTE: 0, SOMENTE_ODOO: 0, SOMENTE_FATURA: 0, PENDENTE_REVISAO: 0,
  total_fatura: 0, total_odoo: 0, valor_conciliado: 0, diferenca_fontes: 0,
  total_lancamentos_fatura: 0, total_lancamentos_odoo: 0, percentual_conciliado: 0,
  total_invoice: 0, total_odoo_count: 0, conciliated: 0, divergent: 0, pending: 0, only_invoice: 0, only_odoo: 0,
};

const numeric = (value: string | number | null | undefined): number => {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
};

const money = (value: string | number | null | undefined): string =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numeric(value));

const statusLabel: Record<string, string> = {
  CONCILIADO: 'Conciliado', DIVERGENTE: 'Divergente', PENDENTE_REVISAO: 'Pendente de revisão',
  SOMENTE_ODOO: 'Somente Odoo', SOMENTE_FATURA: 'Somente fatura',
};

function summaryOf(records: Reconciliation[]): Summary {
  if (!records.length) return ZERO_SUMMARY;
  const result: Summary = { ...ZERO_SUMMARY };
  for (const record of records) {
    const s = record.summary;
    result.CONCILIADO += numeric(s.CONCILIADO ?? s.conciliated);
    result.DIVERGENTE += numeric(s.DIVERGENTE ?? s.divergent);
    result.PENDENTE_REVISAO += numeric(s.PENDENTE_REVISAO ?? s.pending);
    result.SOMENTE_FATURA += numeric(s.SOMENTE_FATURA ?? s.only_invoice);
    result.SOMENTE_ODOO += numeric(s.SOMENTE_ODOO ?? s.only_odoo);
    result.total_fatura = numeric(result.total_fatura) + numeric(s.total_fatura);
    result.total_odoo = numeric(result.total_odoo) + numeric(s.total_odoo);
    result.valor_conciliado = numeric(result.valor_conciliado) + numeric(s.valor_conciliado);
    result.total_lancamentos_fatura += numeric(s.total_lancamentos_fatura ?? s.total_invoice);
    result.total_lancamentos_odoo += numeric(s.total_lancamentos_odoo ?? s.total_odoo_count);
  }
  result.diferenca_fontes = numeric(result.total_fatura) - numeric(result.total_odoo);
  result.percentual_conciliado = result.total_lancamentos_fatura
    ? 100 * result.CONCILIADO / result.total_lancamentos_fatura : 0;
  result.total_invoice = result.total_lancamentos_fatura;
  result.total_odoo_count = result.total_lancamentos_odoo;
  result.conciliated = result.CONCILIADO;
  result.divergent = result.DIVERGENTE;
  result.pending = result.PENDENTE_REVISAO;
  result.only_invoice = result.SOMENTE_FATURA;
  result.only_odoo = result.SOMENTE_ODOO;
  return result;
}

function LoginPage({ onLogin }: { onLogin: (email: string, name: string) => Promise<void> }) {
  const [email, setEmail] = useState('analista@grupoepa.local');
  const [name, setName] = useState('Analista Grupo EPA');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try { await onLogin(email.trim(), name.trim()); }
    catch (err) { setError(getApiError(err, 'Não foi possível iniciar a sessão.')); }
    finally { setLoading(false); }
  };

  return (
    <div className="login-screen">
      <section className="login-art">
        <div className="art-grid" />
        <div className="art-orbit orbit-one" />
        <div className="art-orbit orbit-two" />
        <div className="login-art-content">
          <img src="/epa-logo.png" alt="Logo Grupo EPA" />
          <div className="art-kicker">GESTÃO FINANCEIRA • CONTROLE E CONFIABILIDADE</div>
          <h1>Conciliação com <em>precisão.</em><br />Decisões com confiança.</h1>
          <p>Centralize faturas bancárias e lançamentos do Odoo em um fluxo rastreável, explicável e seguro.</p>
          <div className="art-features">
            <span><ShieldCheck size={14} /> Rastreabilidade</span>
            <span><Activity size={14} /> Indicadores reais</span>
            <span><ListChecks size={14} /> Revisão controlada</span>
          </div>
        </div>
        <div className="art-footer">GRUPO EPA <i>•</i> CONCILIAÇÃO FINANCEIRA</div>
      </section>
      <section className="login-panel">
        <div className="login-box">
          <div className="eyebrow"><span className="eyebrow-line" /> ACESSO AO SISTEMA</div>
          <h2>Bem-vindo</h2>
          <p>Entre para acessar os processos de conciliação bancária.</p>
          <div className="dev-warning">
            <AlertCircle size={16} />
            <span><b>Autenticação de desenvolvimento.</b> Este acesso local não é o login corporativo Microsoft Entra ID.</span>
          </div>
          {error && <div className="alert-box" role="alert">{error}</div>}
          <form className="login-form" onSubmit={submit}>
            <label>Nome de exibição<input value={name} onChange={(e) => setName(e.target.value)} required maxLength={160} /></label>
            <label>E-mail corporativo<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required maxLength={255} /></label>
            <button className="btn btn-primary login-submit" type="submit" disabled={loading}>
              <LockKeyhole size={15} /> {loading ? 'Conectando...' : 'Acessar sistema'}
            </button>
          </form>
          <div className="login-legal"><ShieldCheck size={13} /> Sessão individual de desenvolvimento</div>
        </div>
      </section>
    </div>
  );
}

function Kpi({ label, value, icon, tone = 'blue', caption }: { label: string; value: string; icon: ReactNode; tone?: string; caption?: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-top"><span>{label}</span><span className={`kpi-icon ${tone}`}>{icon}</span></div>
      <strong>{value}</strong>
      <small>{caption ?? 'Dados processados nesta sessão'}</small>
      <div className={`kpi-bottom ${tone}`}><span /></div>
    </div>
  );
}

function Dashboard({ summary, records, loading, onOpen, onNew, onHistory }: {
  summary: Summary; records: Reconciliation[]; loading: boolean;
  onOpen: (id: number) => void; onNew: () => void; onHistory: () => void;
}) {
  const total = summary.CONCILIADO + summary.DIVERGENTE + summary.PENDENTE_REVISAO + summary.SOMENTE_FATURA + summary.SOMENTE_ODOO;
  const risk = summary.DIVERGENTE + summary.PENDENTE_REVISAO;
  return (
    <div className="page-stack">
      <div className="welcome-row">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> PAINEL OPERACIONAL</div>
          <h1>Visão geral da conciliação</h1>
          <p>Indicadores consolidados a partir dos lotes importados e processados.</p>
        </div>
        <div className="result-actions">
          <button className="btn btn-outline" type="button" onClick={onHistory}><History size={14} /> Histórico</button>
          <button className="btn btn-primary" type="button" onClick={onNew}><Plus size={15} /> Nova conciliação</button>
        </div>
      </div>

      <section className="dashboard-hero">
        <div className="hero-left">
          <div className="hero-chip">{risk ? 'REVISÃO NECESSÁRIA' : total ? 'PROCESSAMENTO CONCLUÍDO' : 'AGUARDANDO IMPORTAÇÕES'}</div>
          <h2>Controle financeiro <span>centralizado.</span></h2>
          <p>{total ? `${total} resultados classificados nos lotes listados. ${risk} exigem atenção ou revisão.` : 'Inicie uma conciliação para visualizar indicadores reais. Nenhum dado de demonstração é exibido.'}</p>
          <div className="hero-actions"><button className="btn btn-primary" type="button" onClick={onNew}><UploadCloud size={14} /> Importar arquivos</button></div>
        </div>
        <div className="hero-graphic" aria-hidden="true">
          <div className="hero-ring ring-a" /><div className="hero-ring ring-b" /><div className="hero-ring ring-c" />
          <div className="hero-stat"><span>TAXA DE CONCILIAÇÃO</span><b>{summary.percentual_conciliado.toFixed(1)}%</b><small>sobre os lançamentos da fatura</small></div>
          <div className="hero-orb"><Wallet size={25} /></div>
        </div>
      </section>

      <section className="kpi-grid">
        <Kpi label="Valor total das faturas" value={money(summary.total_fatura)} icon={<Wallet />} tone="blue" caption={`${summary.total_lancamentos_fatura} lançamentos`} />
        <Kpi label="Valor total Odoo" value={money(summary.total_odoo)} icon={<FileSpreadsheet />} tone="violet" caption={`${summary.total_lancamentos_odoo} lançamentos`} />
        <Kpi label="Lançamentos conciliados" value={String(summary.CONCILIADO)} icon={<CheckCircle2 />} tone="green" caption={`${summary.percentual_conciliado.toFixed(1)}% da fatura`} />
        <Kpi label="Divergências e pendências" value={String(risk)} icon={<AlertCircle />} tone="red" caption={`${summary.DIVERGENTE} divergentes • ${summary.PENDENTE_REVISAO} pendentes`} />
      </section>

      <section className="section-heading"><div><h2>Últimas conciliações</h2><p>Acompanhe lotes recentes e abra seus resultados.</p></div><button className="text-btn" type="button" onClick={onHistory}>Ver histórico completo →</button></section>
      <div className="panel recent-panel">
        {loading ? <div className="empty-state"><RefreshCw className="spin" /> Carregando conciliações...</div> : records.length === 0 ? (
          <div className="empty-state"><FileText size={24} /><b>Nenhuma conciliação encontrada</b><span>Importe uma fatura e o arquivo do Odoo para começar.</span><button className="btn btn-primary" onClick={onNew} type="button"><Plus size={14} /> Nova conciliação</button></div>
        ) : (
          <div className="table-wrap"><table><thead><tr><th>Identificação</th><th>Banco</th><th>Status</th><th>Data</th><th>Conciliados</th><th></th></tr></thead>
            <tbody>{records.slice(0, 5).map((rec) => <tr key={rec.id}>
              <td><b>{rec.name}</b><small className="table-sub">Lote #{rec.id}</small></td>
              <td><span className={`badge-bank ${rec.bank.toLowerCase()}`}>{rec.bank}</span></td>
              <td><span className={`status-pill ${rec.status === 'PROCESSADA' ? 'success' : 'pending'}`}>{rec.status === 'PROCESSADA' ? 'Processada' : 'Em preparação'}</span></td>
              <td>{new Date(rec.created_at).toLocaleDateString('pt-BR')}</td>
              <td>{rec.summary.CONCILIADO ?? rec.summary.conciliated ?? 0}</td>
              <td><button className="btn btn-outline" type="button" onClick={() => onOpen(rec.id)}>Abrir</button></td>
            </tr>)}</tbody></table></div>
        )}
      </div>
    </div>
  );
}

const mappingFields: Array<{ key: string; label: string }> = [
  { key: 'date', label: 'Data' }, { key: 'name', label: 'Parceiro / estabelecimento' },
  { key: 'description', label: 'Descrição / rótulo' }, { key: 'reference', label: 'Referência / número' },
  { key: 'debit', label: 'Débito' }, { key: 'credit', label: 'Crédito' }, { key: 'amount', label: 'Valor / total' },
  { key: 'kind', label: 'Tipo / natureza' },
];

function NewReconciliation({ onPrepared, onError }: { onPrepared: (detail: ReconciliationDetail) => void; onError: (message: string) => void }) {
  const [name, setName] = useState(`Conciliação ${new Date().toLocaleDateString('pt-BR')}`);
  const [bank, setBank] = useState<'ITAU' | 'SANTANDER'>('ITAU');
  const [tolerance, setTolerance] = useState(3);
  const [periodStart, setPeriodStart] = useState('');
  const [periodEnd, setPeriodEnd] = useState('');
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [odooFile, setOdooFile] = useState<File | null>(null);
  const [odooPreview, setOdooPreview] = useState<OdooPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const selectOdoo = async (file: File | null) => {
    setOdooFile(file); setOdooPreview(null); setMapping({});
    if (!file) return;
    setPreviewing(true);
    try {
      const preview = await api.previewOdoo(file);
      setOdooPreview(preview);
      setMapping(preview.suggested_mapping ?? {});
    } catch (err) { onError(getApiError(err, 'Não foi possível identificar as colunas do arquivo Odoo.')); }
    finally { setPreviewing(false); }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!invoiceFile || !odooFile) { onError('Selecione a fatura bancária e a planilha do Odoo.'); return; }
    const invoiceExt = invoiceFile.name.split('.').pop()?.toLowerCase();
    if (bank === 'ITAU' && invoiceExt !== 'pdf') { onError('Para Itaú, selecione uma fatura PDF.'); return; }
    if (bank === 'SANTANDER' && !['png', 'jpg', 'jpeg'].includes(invoiceExt ?? '')) { onError('Para Santander, selecione uma imagem PNG ou JPG.'); return; }
    if (odooPreview && !mapping.date) { onError('Mapeie a coluna de data da planilha Odoo.'); return; }
    setSubmitting(true);
    let newId: number | null = null;
    try {
      const created = await api.create({ name, bank, tolerance_days: tolerance, period_start: periodStart || null, period_end: periodEnd || null });
      newId = created.id;
      await api.upload(created.id, 'invoice', invoiceFile);
      await api.upload(created.id, 'odoo', odooFile, mapping);
      const detail = await api.detail(created.id);
      onPrepared(detail);
    } catch (err) {
      const detail = getApiError(err, 'Não foi possível importar os arquivos.');
      onError(newId ? `${detail} O lote ${newId} foi criado; confira o histórico para retomar a revisão.` : detail);
    } finally { setSubmitting(false); }
  };

  const accept = bank === 'ITAU' ? '.pdf,application/pdf' : '.png,.jpg,.jpeg,image/png,image/jpeg';
  return (
    <div className="page-stack">
      <div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-line" /> NOVO PROCESSAMENTO</div><h1>Nova conciliação</h1><p>Informe o banco, revise o mapeamento e importe os dois arquivos.</p></div></div>
      <form className="panel new-form-panel" onSubmit={submit}>
        <div className="form-section-title"><span className="step-number">01</span><div><b>Identificação do lote</b><small>Defina os parâmetros financeiros do processamento.</small></div></div>
        <div className="form-grid">
          <label className="field"><span>Identificação</span><input value={name} onChange={(e) => setName(e.target.value)} minLength={3} maxLength={180} required /></label>
          <label className="field"><span>Instituição bancária</span><select value={bank} onChange={(e) => { setBank(e.target.value as 'ITAU' | 'SANTANDER'); setInvoiceFile(null); }}><option value="ITAU">Itaú</option><option value="SANTANDER">Santander</option></select></label>
          <label className="field"><span>Tolerância de data (dias)</span><input type="number" min={0} max={60} value={tolerance} onChange={(e) => setTolerance(Math.max(0, Math.min(60, Number(e.target.value || 0))))} /></label>
          <label className="field"><span>Data inicial (opcional)</span><input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} /></label>
          <label className="field"><span>Data final (opcional)</span><input type="date" value={periodEnd} min={periodStart || undefined} onChange={(e) => setPeriodEnd(e.target.value)} /></label>
        </div>
        <div className="form-section-title section-spaced"><span className="step-number">02</span><div><b>Arquivos de origem</b><small>O arquivo original será preservado no armazenamento da conciliação.</small></div></div>
        <div className="upload-grid">
          <label className="upload-card"><input type="file" accept={accept} onChange={(e) => setInvoiceFile(e.target.files?.[0] ?? null)} required />
            <span className="upload-icon"><FileText size={21} /></span><b>Fatura {bank === 'ITAU' ? 'Itaú (PDF)' : 'Santander (imagem)'}</b><small>{bank === 'ITAU' ? 'PDF com texto ou digitalizado' : 'Imagem PNG, JPG ou JPEG'}</small>
            <span className="file-selected">{invoiceFile ? invoiceFile.name : 'Selecionar arquivo'}</span>
          </label>
          <label className="upload-card"><input type="file" accept=".xlsx,.xlsm,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel.sheet.macroEnabled.12" onChange={(e) => void selectOdoo(e.target.files?.[0] ?? null)} required />
            <span className="upload-icon"><FileSpreadsheet size={21} /></span><b>Exportação do Odoo</b><small>Planilha Excel XLSX ou XLSM</small>
            <span className="file-selected">{odooFile ? odooFile.name : 'Selecionar planilha'}</span>
            {previewing && <span className="mapping-ready">Analisando cabeçalhos...</span>}
          </label>
        </div>
        {odooPreview && (
          <div className="mapping-panel">
            <div className="mapping-head"><div><b>Mapeamento das colunas Odoo</b><small>Aba: {odooPreview.sheet} • Cabeçalho na linha {odooPreview.header_row} • {odooPreview.total_detected} registros identificados</small></div><span className="mapping-ready"><CheckCircle2 size={12} /> Pré-análise concluída</span></div>
            <div className="mapping-grid">
              {mappingFields.map((field) => <label className="field" key={field.key}><span>{field.label}{field.key === 'date' ? ' *' : ''}</span><select value={mapping[field.key] ?? ''} onChange={(e) => setMapping((old) => ({ ...old, [field.key]: e.target.value }))}><option value="">Não mapear</option>{odooPreview.columns.map((column, idx) => <option key={`${idx}-${column}`} value={column}>{column}</option>)}</select></label>)}
            </div>
            {odooPreview.unknown_columns.length > 0 && <div className="unknown-columns"><AlertCircle size={13} /> Colunas adicionais preservadas: {odooPreview.unknown_columns.join(', ')}</div>}
          </div>
        )}
        <div className="form-actions"><span className="review-footnote"><ShieldCheck size={14} /> A conciliação automática só ocorrerá após a revisão dos lançamentos importados.</span>
          <button className="btn btn-primary" type="submit" disabled={submitting || previewing || !invoiceFile || !odooFile}><UploadCloud size={15} /> {submitting ? 'Importando arquivos...' : 'Importar e revisar lançamentos'}</button></div>
      </form>
    </div>
  );
}

function SummaryCards({ summary }: { summary: Summary }) {
  return <div className="summary-status-grid">
    <div className="summary-status success"><small>Conciliados</small><b>{summary.CONCILIADO}</b></div>
    <div className="summary-status danger"><small>Divergentes</small><b>{summary.DIVERGENTE}</b></div>
    <div className="summary-status pending"><small>Pendentes</small><b>{summary.PENDENTE_REVISAO}</b></div>
    <div className="summary-status"><small>Somente fatura</small><b>{summary.SOMENTE_FATURA}</b></div>
    <div className="summary-status"><small>Somente Odoo</small><b>{summary.SOMENTE_ODOO}</b></div>
  </div>;
}

function TransactionEditor({ detail, transaction, onClose, onSaved }: {
  detail: ReconciliationDetail; transaction: Transaction; onClose: () => void; onSaved: () => Promise<void>;
}) {
  const [form, setForm] = useState({ date: transaction.date, merchant: transaction.merchant, description: transaction.description, amount: String(transaction.amount), kind: transaction.kind, reference: transaction.reference, justification: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError('');
    try {
      await api.updateTransaction(detail.id, transaction.id, { ...form, justification: form.justification });
      await onSaved(); onClose();
    } catch (err) { setError(getApiError(err)); }
    finally { setSaving(false); }
  };
  const change = (key: keyof typeof form, value: string) => setForm((old) => ({ ...old, [key]: value }));
  return <div className="modal-scrim" role="presentation" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}><div className="modal-card edit-transaction-modal" role="dialog" aria-modal="true" aria-labelledby="edit-title">
    <div className="modal-head"><div><b id="edit-title">Revisar lançamento</b><small>{transaction.source === 'FATURA' ? 'Origem: fatura bancária' : 'Origem: Odoo'} • ID {transaction.id}</small></div><button className="icon-btn" type="button" onClick={onClose} aria-label="Fechar"><X size={16} /></button></div>
    <form onSubmit={submit} className="modal-form">
      <div className="form-grid"><label className="field"><span>Data</span><input type="date" value={form.date} onChange={(e) => change('date', e.target.value)} required /></label>
        <label className="field"><span>Valor</span><input value={form.amount} onChange={(e) => change('amount', e.target.value)} required /></label>
        <label className="field"><span>Estabelecimento / parceiro</span><input value={form.merchant} onChange={(e) => change('merchant', e.target.value)} required /></label>
        <label className="field"><span>Natureza</span><select value={form.kind} onChange={(e) => change('kind', e.target.value)}><option value="">Não identificada</option><option value="COMPRA">Compra</option><option value="DEBITO">Débito</option><option value="CREDITO">Crédito</option><option value="ESTORNO">Estorno</option><option value="IOF">IOF</option><option value="TAXA">Taxa / encargo</option></select></label>
        <label className="field full"><span>Descrição</span><input value={form.description} onChange={(e) => change('description', e.target.value)} /></label>
        <label className="field full"><span>Referência</span><input value={form.reference} onChange={(e) => change('reference', e.target.value)} /></label>
        <label className="field full"><span>Justificativa da revisão (obrigatória)</span><textarea value={form.justification} onChange={(e) => change('justification', e.target.value)} minLength={8} required rows={3} /></label>
      </div>
      {error && <div className="alert-box">{error}</div>}
      <div className="modal-actions"><button className="btn btn-outline" type="button" onClick={onClose}>Cancelar</button><button className="btn btn-primary" type="submit" disabled={saving}>{saving ? 'Salvando...' : 'Salvar revisão'}</button></div>
    </form>
  </div></div>;
}

function ResultsPage({ detail, onBack, onRefresh, onError }: {
  detail: ReconciliationDetail; onBack: () => void; onRefresh: () => Promise<void>; onError: (message: string) => void;
}) {
  const [tab, setTab] = useState<ResultTab>('TODOS');
  const [processing, setProcessing] = useState(false);
  const [editTransaction, setEditTransaction] = useState<Transaction | null>(null);
  const [invoiceId, setInvoiceId] = useState('');
  const [odooId, setOdooId] = useState('');
  const [manualStatus, setManualStatus] = useState<'CONCILIADO' | 'DIVERGENTE'>('CONCILIADO');
  const [justification, setJustification] = useState('');
  const [manualBusy, setManualBusy] = useState(false);
  const [undoJustification, setUndoJustification] = useState('');
  const [undoBusy, setUndoBusy] = useState<number | null>(null);
  const summary = useMemo(() => ({ ...ZERO_SUMMARY, ...detail.summary }), [detail.summary]);
  const processed = detail.status === 'PROCESSADA';
  const results = detail.results ?? [];
  const filteredResults = tab === 'TODOS' ? results : results.filter((item) => item.status === tab);

  const runProcess = async () => {
    setProcessing(true);
    try { await api.process(detail.id); await onRefresh(); }
    catch (err) { onError(getApiError(err, 'Falha ao executar o motor de conciliação.')); }
    finally { setProcessing(false); }
  };

  const doManualMatch = async (event: FormEvent) => {
    event.preventDefault();
    if (!invoiceId || !odooId || justification.trim().length < 8) { onError('Selecione os dois lançamentos e informe uma justificativa com pelo menos 8 caracteres.'); return; }
    setManualBusy(true);
    try {
      await api.manualMatch(detail.id, { invoice_transaction_id: Number(invoiceId), odoo_transaction_id: Number(odooId), status: manualStatus, justification: justification.trim() });
      setInvoiceId(''); setOdooId(''); setJustification(''); await onRefresh();
    } catch (err) { onError(getApiError(err, 'Não foi possível registrar a associação manual.')); }
    finally { setManualBusy(false); }
  };

  const undo = async (matchId: number) => {
    if (undoJustification.trim().length < 8) { onError('Informe uma justificativa com pelo menos 8 caracteres para desfazer o resultado.'); return; }
    setUndoBusy(matchId);
    try { await api.undoMatch(detail.id, matchId, undoJustification.trim()); setUndoJustification(''); await onRefresh(); }
    catch (err) { onError(getApiError(err, 'Não foi possível desfazer a associação.')); }
    finally { setUndoBusy(null); }
  };

  const availableInvoice = detail.transactions.invoice.filter((tx) => !results.some((m) => m.status !== 'PENDENTE_REVISAO' && m.invoice?.id === tx.id && m.status !== 'SOMENTE_FATURA'));
  const availableOdoo = detail.transactions.odoo.filter((tx) => !results.some((m) => m.status !== 'PENDENTE_REVISAO' && m.odoo?.id === tx.id && m.status !== 'SOMENTE_ODOO'));

  return (
    <div className="page-stack">
      <div className="welcome-row"><div><button className="text-btn" type="button" onClick={onBack}><ArrowLeft size={13} /> Voltar ao painel</button><div className="eyebrow"><span className="eyebrow-line" /> RESULTADO DO PROCESSAMENTO</div><h1>{detail.name}</h1><p>{detail.bank} • Lote #{detail.id} • Tolerância de {detail.tolerance_days} dia(s)</p></div>
        <div className="result-actions">{processed && <>{(['xlsx', 'csv', 'pdf'] as const).map((format) => <button className="btn btn-outline" type="button" key={format} onClick={() => void api.exportFile(detail.id, format).catch((err) => onError(getApiError(err)))}><Download size={13} /> {format.toUpperCase()}</button>)}</>}
          {!processed && <button className="btn btn-primary" type="button" disabled={processing || !detail.transactions.invoice.length || !detail.transactions.odoo.length} onClick={() => void runProcess()}>{processing ? <RefreshCw size={14} className="spin" /> : <CheckCircle2 size={14} />} {processing ? 'Processando...' : 'Executar conciliação'}</button>}</div>
      </div>

      <div className="financial-overview">
        <div className="financial-card"><small>Total da fatura</small><strong>{money(summary.total_fatura)}</strong><span>{summary.total_lancamentos_fatura} lançamentos</span></div>
        <div className="financial-card"><small>Total normalizado do Odoo</small><strong>{money(summary.total_odoo)}</strong><span>{summary.total_lancamentos_odoo} lançamentos</span></div>
        <div className="financial-card"><small>Valor conciliado</small><strong>{money(summary.valor_conciliado)}</strong><span>{summary.percentual_conciliado.toFixed(1)}% dos registros da fatura</span></div>
        <div className="financial-card"><small>Diferença entre fontes</small><strong className={numeric(summary.diferenca_fontes) ? 'text-danger' : 'text-success'}>{money(summary.diferenca_fontes)}</strong><span>Após normalização de débito/crédito</span></div>
      </div>

      {!processed ? (
        <>
          <div className="review-callout panel"><div className="review-callout-icon"><ListChecks size={18} /></div><div><b>Prévia importada — revisão antes da conciliação</b><p>Confira os nomes, datas, valores e natureza. Os totais abaixo são calculados a partir dos registros importados; ainda não há resultados de conciliação.</p></div></div>
          <div className="review-grid">
            <SourceTable title="Fatura bancária" rows={detail.transactions.invoice} onEdit={setEditTransaction} />
            <SourceTable title="Lançamentos Odoo" rows={detail.transactions.odoo} onEdit={setEditTransaction} />
          </div>
        </>
      ) : (
        <>
          <SummaryCards summary={summary} />
          <div className="result-tabs">{([
            ['TODOS', 'Todos'], ['CONCILIADO', 'Conciliados'], ['DIVERGENTE', 'Divergentes'], ['PENDENTE_REVISAO', 'Pendentes'], ['SOMENTE_ODOO', 'Somente Odoo'], ['SOMENTE_FATURA', 'Somente fatura'],
          ] as Array<[ResultTab, string]>).map(([key, label]) => <button key={key} type="button" className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label} <span>{key === 'TODOS' ? results.length : results.filter((r) => r.status === key).length}</span></button>)}</div>
          <div className="panel result-panel"><div className="table-wrap"><table className="results-table"><thead><tr><th>Status</th><th>Data fatura</th><th>Estabelecimento fatura</th><th>Valor fatura</th><th>Data Odoo</th><th>Parceiro Odoo</th><th>Valor Odoo</th><th>Diferença</th><th>Motivo</th><th>Ação</th></tr></thead>
            <tbody>{filteredResults.length === 0 ? <tr><td colSpan={10}><div className="empty-state">Nenhum resultado nesta categoria.</div></td></tr> : filteredResults.map((r) => <MatchRow key={r.id} result={r} onUndo={() => void undo(r.id)} undoDisabled={undoBusy === r.id || undoJustification.trim().length < 8} />)}</tbody>
          </table></div></div>
          <div className="undo-panel panel"><div><b>Desfazer resultado</b><small>O histórico da operação será preservado na auditoria.</small></div><input value={undoJustification} onChange={(e) => setUndoJustification(e.target.value)} placeholder="Justificativa (mínimo 8 caracteres)" minLength={8} /><span className="field-hint">Informe a justificativa antes de usar a ação em uma linha.</span></div>
          <div className="panel manual-panel"><div className="panel-heading"><div><b>Associação manual</b><small>Use somente após conferir os documentos originais.</small></div></div>
            <form onSubmit={doManualMatch} className="manual-match-form"><label className="field"><span>Lançamento da fatura</span><select value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} required><option value="">Selecione</option>{availableInvoice.map((tx) => <option key={tx.id} value={tx.id}>{tx.date} • {tx.merchant} • {money(tx.amount)}</option>)}</select></label>
              <label className="field"><span>Lançamento Odoo</span><select value={odooId} onChange={(e) => setOdooId(e.target.value)} required><option value="">Selecione</option>{availableOdoo.map((tx) => <option key={tx.id} value={tx.id}>{tx.date} • {tx.merchant} • {money(tx.amount)}</option>)}</select></label>
              <label className="field"><span>Classificação manual</span><select value={manualStatus} onChange={(e) => setManualStatus(e.target.value as 'CONCILIADO' | 'DIVERGENTE')}><option value="CONCILIADO">Conciliado</option><option value="DIVERGENTE">Divergente</option></select></label>
              <label className="field"><span>Justificativa</span><input value={justification} onChange={(e) => setJustification(e.target.value)} minLength={8} placeholder="Motivo da associação" required /></label>
              <button className="btn btn-primary" type="submit" disabled={manualBusy || !invoiceId || !odooId || justification.trim().length < 8}>{manualBusy ? 'Salvando...' : 'Registrar associação'}</button>
            </form>
          </div>
        </>
      )}
      {editTransaction && <TransactionEditor detail={detail} transaction={editTransaction} onClose={() => setEditTransaction(null)} onSaved={onRefresh} />}
    </div>
  );
}

function SourceTable({ title, rows, onEdit }: { title: string; rows: Transaction[]; onEdit: (tx: Transaction) => void }) {
  return <div className="panel preview-source"><div className="panel-heading"><div><b>{title}</b><small>{rows.length} registros importados</small></div></div>
    <div className="table-wrap"><table><thead><tr><th>Data</th><th>Estabelecimento / parceiro</th><th>Valor</th><th>Natureza</th><th></th></tr></thead><tbody>{rows.map((tx) => <tr key={tx.id}><td>{new Date(`${tx.date}T00:00:00`).toLocaleDateString('pt-BR')}</td><td><b>{tx.merchant || 'Nome não informado'}</b><small className="table-sub">{tx.description}</small></td><td>{money(tx.amount)}</td><td>{tx.kind || 'Não identificada'}</td><td><button className="review-edit-btn" type="button" onClick={() => onEdit(tx)}><Pencil size={11} /> Revisar</button></td></tr>)}</tbody></table></div>
    {rows.length === 0 && <div className="empty-state">Nenhum lançamento importado.</div>}
  </div>;
}

function MatchRow({ result, onUndo, undoDisabled }: { result: MatchResult; onUndo: () => void; undoDisabled: boolean }) {
  const f = result.invoice, o = result.odoo;
  const statusClass = result.status === 'CONCILIADO' ? 'success' : result.status === 'DIVERGENTE' ? 'danger' : result.status === 'PENDENTE_REVISAO' ? 'pending' : '';
  const candidates = [result.evidence?.candidate_invoice_ids, result.evidence?.candidate_odoo_ids].filter(Boolean).flat().join(', ');
  return <tr>
    <td><span className={`status-pill ${statusClass}`}>{statusLabel[result.status] ?? result.status}</span></td>
    <td>{f?.date ? new Date(`${f.date}T00:00:00`).toLocaleDateString('pt-BR') : '—'}</td>
    <td>{f?.merchant || (f ? 'Nome não informado' : '—')}</td>
    <td>{f ? money(f.amount) : '—'}</td>
    <td>{o?.date ? new Date(`${o.date}T00:00:00`).toLocaleDateString('pt-BR') : '—'}</td>
    <td>{o?.merchant || (o ? 'Nome não informado' : '—')}</td>
    <td>{o ? money(o.amount) : '—'}</td>
    <td>{result.difference == null ? '—' : money(result.difference)}</td>
    <td className="reason-cell">{result.reason}{candidates && <small className="table-sub">IDs candidatos: {candidates}</small>}</td>
    <td><button className="text-btn danger-text" type="button" disabled={undoDisabled} onClick={onUndo}>Desfazer</button></td>
  </tr>;
}

function HistoryPage({ records, loading, onOpen, onRefresh }: { records: Reconciliation[]; loading: boolean; onOpen: (id: number) => void; onRefresh: () => void }) {
  return <div className="page-stack"><div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-line" /> CONSULTA</div><h1>Histórico de conciliações</h1><p>Consulte lotes anteriores, status e indicadores calculados.</p></div><button className="btn btn-outline" onClick={onRefresh} type="button"><RefreshCw size={14} /> Atualizar</button></div>
    <div className="panel recent-panel">{loading ? <div className="empty-state">Carregando histórico...</div> : records.length === 0 ? <div className="empty-state">Nenhuma conciliação cadastrada.</div> : <div className="table-wrap"><table><thead><tr><th>Lote</th><th>Banco</th><th>Status</th><th>Data</th><th>Conciliados</th><th>Divergentes</th><th>Pendentes</th><th></th></tr></thead><tbody>{records.map((r) => <tr key={r.id}><td><b>{r.name}</b><small className="table-sub">#{r.id}</small></td><td>{r.bank}</td><td>{r.status}</td><td>{new Date(r.created_at).toLocaleString('pt-BR')}</td><td>{r.summary.CONCILIADO ?? 0}</td><td>{r.summary.DIVERGENTE ?? 0}</td><td>{r.summary.PENDENTE_REVISAO ?? 0}</td><td><button type="button" className="btn btn-outline" onClick={() => onOpen(r.id)}>Abrir</button></td></tr>)}</tbody></table></div>}</div>
  </div>;
}

function AuditPage({ logs, loading, onRefresh }: { logs: AuditRecord[]; loading: boolean; onRefresh: () => void }) {
  return <div className="page-stack"><div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-line" /> RASTREABILIDADE</div><h1>Auditoria</h1><p>Registro de importações, revisões e alterações manuais.</p></div><button type="button" className="btn btn-outline" onClick={onRefresh}><RefreshCw size={14} /> Atualizar</button></div>
    <div className="panel recent-panel">{loading ? <div className="empty-state">Carregando auditoria...</div> : logs.length === 0 ? <div className="empty-state">Nenhuma operação registrada.</div> : <div className="table-wrap"><table><thead><tr><th>Data e hora</th><th>Ação</th><th>Entidade</th><th>ID</th><th>Conciliação</th><th>Justificativa</th></tr></thead><tbody>{logs.map((row) => <tr key={row.id}><td>{new Date(row.created_at).toLocaleString('pt-BR')}</td><td>{row.action}</td><td>{row.entity_type}</td><td>{row.entity_id}</td><td>{row.reconciliation_id ?? '—'}</td><td>{row.justification || '—'}</td></tr>)}</tbody></table></div>}</div>
  </div>;
}

export default function App() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [page, setPage] = useState<Page>('dashboard');
  const [records, setRecords] = useState<Reconciliation[]>([]);
  const [detail, setDetail] = useState<ReconciliationDetail | null>(null);
  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<'ok' | 'error' | 'checking'>('checking');

  const loadRecords = useCallback(async () => {
    setLoading(true);
    try { const data = await api.list(); setRecords(data); }
    catch (err) { setError(getApiError(err, 'Não foi possível carregar o histórico.')); }
    finally { setLoading(false); }
  }, []);

  const loadDetail = useCallback(async (id: number) => {
    try { const data = await api.detail(id); setDetail(data); setError(null); return data; }
    catch (err) { setError(getApiError(err, 'Não foi possível abrir a conciliação.')); throw err; }
  }, []);

  const loadAudit = useCallback(async () => {
    setAuditLoading(true);
    try { setLogs(await api.audit()); }
    catch (err) { setError(getApiError(err, 'Não foi possível consultar a auditoria.')); }
    finally { setAuditLoading(false); }
  }, []);

  useEffect(() => {
    let alive = true;
    const token = getToken();
    if (!token) { setCheckingSession(false); return () => { alive = false; }; }
    api.me().then((profile) => { if (alive) setUser(profile); })
      .catch(() => { clearToken(); if (alive) setUser(null); })
      .finally(() => { if (alive) setCheckingSession(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    let alive = true;
    api.health().then(() => { if (alive) setHealth('ok'); }).catch(() => { if (alive) setHealth('error'); });
    return () => { alive = false; };
  }, []);

  useEffect(() => { if (user) void loadRecords(); }, [user, loadRecords]);

  const doLogin = async (email: string, name: string) => {
    const response = await api.login({ email, display_name: name, role: 'ANALISTA' });
    setUser(response.user);
    setPage('dashboard');
  };

  const doLogout = () => { clearToken(); setUser(null); setRecords([]); setDetail(null); setPage('dashboard'); };
  const openDetail = async (id: number) => { await loadDetail(id); setPage('detail'); };
  const refreshDetail = async () => { if (detail) { const updated = await loadDetail(detail.id); setDetail(updated); } await loadRecords(); };
  const summary = useMemo(() => summaryOf(records), [records]);

  if (checkingSession) return <div className="boot-screen"><RefreshCw className="spin" size={22} /><span>Verificando sessão...</span></div>;
  if (!user) return <LoginPage onLogin={doLogin} />;

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand-lockup"><img src="/epa-logo.png" alt="Logo Grupo EPA" /><div className="brand-copy"><span>GRUPO EPA</span><small>CONCILIAÇÃO FINANCEIRA</small></div></div>
      <div className="workspace-label">ESPAÇO DE TRABALHO</div>
      <nav className="side-nav" aria-label="Navegação principal">
        <button className={`nav-item ${page === 'dashboard' ? 'active' : ''}`} type="button" onClick={() => setPage('dashboard')}><LayoutDashboard size={16} /> Dashboard</button>
        <button className={`nav-item ${page === 'new' ? 'active' : ''}`} type="button" onClick={() => setPage('new')}><Plus size={16} /> Nova conciliação</button>
        <button className={`nav-item ${page === 'history' ? 'active' : ''}`} type="button" onClick={() => setPage('history')}><History size={16} /> Histórico</button>
        <button className={`nav-item ${page === 'detail' ? 'active' : ''}`} type="button" disabled={!detail} onClick={() => detail && setPage('detail')}><ListChecks size={16} /> Resultados</button>
        <button className={`nav-item ${page === 'audit' ? 'active' : ''}`} type="button" onClick={() => { setPage('audit'); void loadAudit(); }}><ShieldCheck size={16} /> Auditoria</button>
      </nav>
      <div className="sidebar-divider" />
      <div className="sidebar-bottom">
        <div className="system-health"><span className={`health-dot ${health === 'error' ? 'health-error' : ''}`} /><div><b>{health === 'ok' ? 'API conectada' : health === 'error' ? 'API indisponível' : 'Verificando API'}</b><small>{health === 'ok' ? 'Comunicação estabelecida' : health === 'error' ? 'Confira o servidor' : 'Consultando servidor...'}</small></div></div>
        <div className="profile-row"><div className="avatar">{(user.name || 'GE').slice(0, 2).toUpperCase()}</div><div className="profile-copy"><b>{user.name}</b><small>{user.role} • desenvolvimento</small></div><button className="logout-btn" type="button" title="Sair" onClick={doLogout}><LogOut size={15} /></button></div>
      </div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="topbar-left"><div className="breadcrumbs"><span>Grupo EPA</span><b>›</b><span>{({ dashboard: 'Dashboard', new: 'Nova conciliação', detail: 'Resultados', history: 'Histórico', audit: 'Auditoria' } as Record<Page, string>)[page]}</span></div></div><div className="topbar-right"><div className={`env-pill ${health === 'error' ? 'env-error' : ''}`}><span /> {health === 'ok' ? 'API ONLINE' : health === 'error' ? 'API OFFLINE' : 'CONECTANDO'}</div><div className="topbar-date">{new Date().toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })}</div></div></header>
      <main className="page-content">
        {error && <div className="alert-box" role="alert"><AlertCircle size={15} /><span>{error}</span><button type="button" aria-label="Fechar alerta" onClick={() => setError(null)}><X size={14} /></button></div>}
        {page === 'dashboard' && <Dashboard summary={summary} records={records} loading={loading} onOpen={(id) => void openDetail(id)} onNew={() => { setError(null); setPage('new'); }} onHistory={() => setPage('history')} />}
        {page === 'new' && <NewReconciliation onPrepared={(d) => { setDetail(d); setPage('detail'); setError(null); }} onError={setError} />}
        {page === 'detail' && detail && <ResultsPage detail={detail} onBack={() => setPage('dashboard')} onRefresh={refreshDetail} onError={setError} />}
        {page === 'history' && <HistoryPage records={records} loading={loading} onOpen={(id) => void openDetail(id)} onRefresh={() => void loadRecords()} />}
        {page === 'audit' && <AuditPage logs={logs} loading={auditLoading} onRefresh={() => void loadAudit()} />}
      </main>
      <footer className="app-footer"><span>GRUPO EPA <i>•</i> CONCILIAÇÃO BANCÁRIA</span><span>Ambiente de desenvolvimento / homologação</span></footer>
    </div>
  </div>;
}
