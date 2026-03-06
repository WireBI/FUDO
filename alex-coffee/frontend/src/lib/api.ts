let baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Ensure protocol is present to avoid relative path issues
if (baseUrl && !baseUrl.startsWith('http://') && !baseUrl.startsWith('https://')) {
  // If it doesn't have a protocol, assume https for production-like URLs
  baseUrl = `https://${baseUrl}`;
}

const API_URL = baseUrl;

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

async function fetchAPIWithAuth<T>(path: string, adminKey: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export type Period = "today" | "week" | "month" | "year" | "custom";

export interface OverviewData {
  revenue: number;
  revenue_change: number;
  orders: number;
  orders_change: number;
  avg_ticket: number;
  items_sold: number;
  period: string;
}

export interface SalesTrendPoint {
  date: string;
  revenue: number;
  orders: number;
}

export interface TopProduct {
  name: string;
  revenue: number;
  quantity: number;
}

export interface CategorySales {
  category: string;
  revenue: number;
  quantity: number;
}

export interface HourlyData {
  hour: number;
  revenue: number;
  count: number;
}

export interface RecentSale {
  id: number;
  order_number: string | null;
  product: string;
  quantity: number;
  total: number;
  payment_method: string | null;
  date: string;
}

export interface SyncResult {
  status: string;
  categories?: number;
  products?: number;
  sales?: number;
  error?: string;
}

export interface SyncStatus {
  recent_syncs: {
    id: number;
    type: string;
    status: string;
    records_synced: number;
    error: string | null;
    started_at: string | null;
    completed_at: string | null;
  }[];
}

export interface CredentialResponse {
  id: number;
  fudo_api_id: string | null;
  fudo_api_secret_masked: string;
  updated_at: string;
  updated_by: string | null;
}

export interface CredentialStatus {
  configured: boolean;
  source: "database" | "environment" | "none";
  updated_at?: string;
  updated_by?: string;
  note: string;
}

export const api = {
  dashboard: {
    overview: (period: Period, startDate?: string, endDate?: string) => {
      let url = `/api/dashboard/overview?period=${period}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      return fetchAPI<OverviewData>(url);
    },
    salesTrend: (period: Period, startDate?: string, endDate?: string) => {
      let url = `/api/dashboard/sales-trend?period=${period}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      return fetchAPI<SalesTrendPoint[]>(url);
    },
    topProducts: (period: Period, limit = 10, startDate?: string, endDate?: string) => {
      let url = `/api/dashboard/top-products?period=${period}&limit=${limit}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      return fetchAPI<TopProduct[]>(url);
    },
    salesByCategory: (period: Period, startDate?: string, endDate?: string) => {
      let url = `/api/dashboard/sales-by-category?period=${period}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      return fetchAPI<CategorySales[]>(url);
    },
    hourlyDistribution: (period: Period, startDate?: string, endDate?: string) => {
      let url = `/api/dashboard/hourly-distribution?period=${period}`;
      if (startDate) url += `&start_date=${startDate}`;
      if (endDate) url += `&end_date=${endDate}`;
      return fetchAPI<HourlyData[]>(url);
    },
    recentSales: (limit = 20) =>
      fetchAPI<RecentSale[]>(`/api/dashboard/recent-sales?limit=${limit}`),
  },
  sync: {
    trigger: (daysBack = 30) =>
      fetchAPI<SyncResult>(`/api/sync?days_back=${daysBack}`, { method: "POST" }),
    status: () => fetchAPI<SyncStatus>("/api/sync/status"),
    health: () => fetchAPI<{ fudo_api: string }>("/api/sync/health"),
  },
  admin: {
    getCredentials: (adminKey: string) =>
      fetchAPIWithAuth<CredentialResponse | null>("/api/admin/credentials", adminKey),
    updateCredentials: (adminKey: string, secret: string, id?: string) =>
      fetchAPIWithAuth<{ status: string; message: string; updated_at: string }>(
        "/api/admin/credentials",
        adminKey,
        {
          method: "POST",
          body: JSON.stringify({ fudo_api_secret: secret, fudo_api_id: id }),
        }
      ),
    checkStatus: (adminKey: string) =>
      fetchAPIWithAuth<CredentialStatus>("/api/admin/credentials/status", adminKey),
  },
};
