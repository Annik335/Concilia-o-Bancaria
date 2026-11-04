import type { Reconciliation, ReconciliationDetail } from '../types';
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const tokenKey = 'epa_access_token';
export const getToken = () => sessionStorage.getItem(tokenKey);
export function clearToken(){ sessionStorage.removeItem(tokenKey); }
async function request<T>(path:string, init:RequestInit = {}):Promise<T>{
  const headers = new Headers(init.headers || {});
  const token = getToken(); if(token) headers.set('Authorization',`Bearer ${token}`);
  if(init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type','application/json');
  const response = await fetch(`${API}${path}`,{...init,headers});
  if(!response.ok){
    let message = `Erro ${response.status}`;
    try { const data = await response.json(); message = data.detail || data.message || message; } catch {}
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
export const api = {
  login:(email:string,name:string,role:string='ANALISTA')=>request<{access_token:string;user:{id:number;email:string;name:string;role:string};warning:string}>('/auth/dev-login',{method:'POST',body:JSON.stringify({email,display_name:name,role})}),
  me:()=>request<{id:number;email:string;name:string;role:string}>('/me'),
  list:()=>request<Reconciliation[]>('/reconciliations'),
  detail:(id:number)=>request<ReconciliationDetail>(`/reconciliations/${id}`),
  create:(payload:Record<string,any>)=>request<{id:number;name:string;bank:string;status:string}>('/reconciliations',{method:'POST',body:JSON.stringify(payload)}),
  upload:(id:number,source:'invoice'|'odoo',file:File,mapping?:Record<string,string>)=>{const form=new FormData();form.append('file',file);if(mapping&&source==='odoo')form.append('mapping_json',JSON.stringify(mapping));return request<{import_id:number;imported:number;status:string;metadata:Record<string,any>}>(`/reconciliations/${id}/imports/${source}`,{method:'POST',body:form});},
  previewOdoo:(file:File)=>{const form=new FormData();form.append('file',file);return request<any>('/imports/odoo/preview',{method:'POST',body:form});},
  updateTransaction:(id:number,txId:number,payload:Record<string,any>)=>request<any>(`/reconciliations/${id}/transactions/${txId}`,{method:'PATCH',body:JSON.stringify(payload)}),
  process:(id:number)=>request<{reconciliation_id:number;status:string;summary:any}>(`/reconciliations/${id}/process`,{method:'POST'}),
  audit:()=>request<any[]>('/audit'),
  manual:(id:number,payload:Record<string,any>)=>request<any>(`/reconciliations/${id}/matches/manual`,{method:'POST',body:JSON.stringify(payload)}),
  undo:(id:number,matchId:number,justification:string)=>request<any>(`/reconciliations/${id}/matches/${matchId}?justification=${encodeURIComponent(justification)}`,{method:'DELETE'}),
  exportUrl:(id:number,format:string)=>`${API}/reconciliations/${id}/export?format=${format}`,
};
