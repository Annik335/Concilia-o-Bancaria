export type Summary = {
<<<<<<< HEAD
  CONCILIADO: number;
  DIVERGENTE: number;
  SOMENTE_ODOO: number;
  SOMENTE_FATURA: number;
  PENDENTE_REVISAO: number;
  total_fatura: string | number;
  total_odoo: string | number;
  valor_conciliado: string | number;
  diferenca_fontes: string | number;
  total_lancamentos_fatura: number;
  total_lancamentos_odoo: number;
  percentual_conciliado: number;
  total_invoice?: number;
  total_odoo_count?: number;
  conciliated?: number;
  divergent?: number;
  pending?: number;
  only_invoice?: number;
  only_odoo?: number;
  [key: string]: string | number | undefined;
};

export type Transaction = {
  id: number;
  source: string;
  date: string;
  merchant: string;
  description: string;
  amount: string | number;
  kind: string;
  reference: string;
};

export type MatchResult = {
  id: number;
  status: string;
  is_manual: boolean;
  difference: string | number | null;
  confidence: number;
  rule: string;
  reason: string;
  evidence: Record<string, any>;
  invoice: Transaction | null;
  odoo: Transaction | null;
};

export type ImportRecord = {
  id: number;
  filename: string;
  source: string;
  status: string;
  imported_count: number;
  error_message: string;
  metadata: Record<string, any>;
};

export type Reconciliation = {
  id: number;
  name: string;
  bank: string;
  status: string;
  created_at: string;
  period_start?: string | null;
  period_end?: string | null;
  tolerance_days: number;
  summary: Summary;
};

export type ReconciliationDetail = Reconciliation & {
  processed_at: string | null;
  transactions: {
    invoice: Transaction[];
    odoo: Transaction[];
  };
  imports: ImportRecord[];
  results: MatchResult[];
};

export type ReconciliationCreatePayload = {
  name: string;
  bank: 'ITAU' | 'SANTANDER';
  tolerance_days?: number;
  tolerancia_dias?: number;
  period_start?: string | null;
  period_end?: string | null;
};
=======
  CONCILIADO:number; DIVERGENTE:number; SOMENTE_ODOO:number; SOMENTE_FATURA:number; PENDENTE_REVISAO:number;
  total_fatura:string; total_odoo:string; valor_conciliado:string; diferenca_fontes:string;
  total_lancamentos_fatura:number; total_lancamentos_odoo:number; percentual_conciliado:number;
};
export type Transaction = {id:number;source:string;date:string;merchant:string;description:string;amount:string;kind:string;reference:string};
export type MatchResult = {id:number;status:string;is_manual:boolean;difference:string|null;confidence:number;rule:string;reason:string;evidence:Record<string,any>;invoice:Transaction|null;odoo:Transaction|null};
export type Reconciliation = {id:number;name:string;bank:string;status:string;created_at:string;period_start?:string|null;period_end?:string|null;tolerance_days:number;summary:Summary};
export type ReconciliationDetail = Reconciliation & {processed_at:string|null;transactions:{invoice:Transaction[];odoo:Transaction[]};imports:Array<{id:number;filename:string;source:string;status:string;imported_count:number;error_message:string;metadata:Record<string,any>}>;results:MatchResult[]};
>>>>>>> 8c6000e2885993cbbb1fe507be2aeb004eb5c52f
