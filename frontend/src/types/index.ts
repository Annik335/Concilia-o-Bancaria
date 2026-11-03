export type Summary = {
  CONCILIADO:number; DIVERGENTE:number; SOMENTE_ODOO:number; SOMENTE_FATURA:number; PENDENTE_REVISAO:number;
  total_fatura:string; total_odoo:string; valor_conciliado:string; diferenca_fontes:string;
  total_lancamentos_fatura:number; total_lancamentos_odoo:number; percentual_conciliado:number;
};
export type Transaction = {id:number;source:string;date:string;merchant:string;description:string;amount:string;kind:string;reference:string};
export type MatchResult = {id:number;status:string;is_manual:boolean;difference:string|null;confidence:number;rule:string;reason:string;evidence:Record<string,any>;invoice:Transaction|null;odoo:Transaction|null};
export type Reconciliation = {id:number;name:string;bank:string;status:string;created_at:string;period_start?:string|null;period_end?:string|null;tolerance_days:number;summary:Summary};
export type ReconciliationDetail = Reconciliation & {processed_at:string|null;transactions:{invoice:Transaction[];odoo:Transaction[]};imports:Array<{id:number;filename:string;source:string;status:string;imported_count:number;error_message:string;metadata:Record<string,any>}>;results:MatchResult[]};
