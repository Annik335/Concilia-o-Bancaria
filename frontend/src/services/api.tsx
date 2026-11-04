import axios from 'axios';
import type {
  Reconciliation,
  ReconciliationCreatePayload,
  ReconciliationDetail,
  Transaction,
} from '../types';

// All requests use the same-origin /api proxy. This works when the browser is
// opened from another workstation and avoids baking localhost into the build.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '',
  timeout: 45_000,
});

export const getToken = (): string | null => localStorage.getItem('epa_token');
export const clearToken = (): void => localStorage.removeItem('epa_token');

apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export type OdooPreview = {
  sheet: string;
  header_row: number;
  columns: string[];
  suggested_mapping: Record<string, string>;
  unknown_columns: string[];
  sample: Array<Record<string, unknown>>;
  total_detected: number;
  ignored: number;
};

export type AuditRecord = {
  id: number;
  reconciliation_id: number | null;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  justification: string;
  created_at: string;
};

export const api = {
  health: async (): Promise<{ status: string; environment: string }> => {
    const response = await apiClient.get('/api/health');
    return response.data;
  },

  me: async () => {
    const response = await apiClient.get('/api/me');
    return response.data;
  },

  login: async (credentials: { email: string; display_name?: string; role?: string }) => {
    const payload = {
      email: credentials.email,
      display_name: credentials.display_name ?? credentials.email.split('@')[0],
      role: credentials.role ?? 'ANALISTA',
    };
    const response = await apiClient.post('/api/auth/dev-login', payload);
    const token = response.data?.access_token;
    if (!token) throw new Error('A API não retornou um token de sessão.');
    localStorage.setItem('epa_token', token);
    return response.data;
  },

  list: async (): Promise<Reconciliation[]> => {
    const response = await apiClient.get('/api/reconciliations');
    return Array.isArray(response.data) ? response.data : [];
  },

  detail: async (id: number): Promise<ReconciliationDetail> => {
    const response = await apiClient.get(`/api/reconciliations/${id}`);
    return response.data;
  },

  create: async (data: ReconciliationCreatePayload) => {
    const response = await apiClient.post('/api/reconciliations', {
      name: data.name,
      bank: data.bank,
      period_start: data.period_start ?? null,
      period_end: data.period_end ?? null,
      tolerance_days: data.tolerance_days ?? data.tolerancia_dias ?? 3,
    });
    return response.data as { id: number; name: string; bank: string; status: string; tolerance_days: number };
  },

  previewOdoo: async (file: File): Promise<OdooPreview> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/api/imports/odoo/preview', formData);
    return response.data;
  },

  upload: async (id: number, type: 'invoice' | 'odoo', file: File, mapping?: Record<string, string>) => {
    const formData = new FormData();
    formData.append('file', file);
    if (mapping && Object.keys(mapping).length) {
      formData.append('mapping_json', JSON.stringify(mapping));
    }
    const endpoint = type === 'invoice'
      ? `/api/reconciliations/${id}/imports/invoice`
      : `/api/reconciliations/${id}/imports/odoo`;
    const response = await apiClient.post(endpoint, formData, {
      timeout: 180_000,
    });
    return response.data;
  },

  process: async (id: number) => {
    const response = await apiClient.post(`/api/reconciliations/${id}/process`, {}, { timeout: 120_000 });
    return response.data;
  },

  updateTransaction: async (
    reconciliationId: number,
    transactionId: number,
    payload: Partial<Pick<Transaction, 'date' | 'merchant' | 'description' | 'amount' | 'kind' | 'reference'>> & { justification: string },
  ) => {
    const response = await apiClient.patch(
      `/api/reconciliations/${reconciliationId}/transactions/${transactionId}`,
      {
        transaction_date: payload.date,
        merchant: payload.merchant,
        description: payload.description,
        amount: payload.amount == null ? undefined : String(payload.amount),
        kind: payload.kind,
        reference: payload.reference,
        justification: payload.justification,
      },
    );
    return response.data;
  },

  manualMatch: async (reconciliationId: number, payload: {
    invoice_transaction_id: number;
    odoo_transaction_id: number;
    status: 'CONCILIADO' | 'DIVERGENTE';
    justification: string;
  }) => {
    const response = await apiClient.post(`/api/reconciliations/${reconciliationId}/matches/manual`, payload);
    return response.data;
  },

  undoMatch: async (reconciliationId: number, matchId: number, justification: string) => {
    const params = new URLSearchParams({ justification });
    const response = await apiClient.delete(`/api/reconciliations/${reconciliationId}/matches/${matchId}?${params.toString()}`);
    return response.data;
  },

  audit: async (): Promise<AuditRecord[]> => {
    const response = await apiClient.get('/api/audit');
    return Array.isArray(response.data) ? response.data : [];
  },

  exportFile: async (reconciliationId: number, format: 'xlsx' | 'csv' | 'pdf') => {
    const response = await apiClient.get(`/api/reconciliations/${reconciliationId}/export`, {
      params: { format },
      responseType: 'blob',
      timeout: 60_000,
    });
    const blob = new Blob([response.data]);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `grupo-epa-conciliacao-${reconciliationId}.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export function getApiError(error: unknown, fallback = 'Não foi possível concluir a operação.'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (error.code === 'ECONNABORTED') return 'A operação excedeu o tempo limite. Verifique a conexão com o servidor.';
    if (!error.response) return 'Não foi possível conectar à API. Verifique se o sistema está iniciado.';
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
