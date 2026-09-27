const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('farmo_token');
}

export interface ApiError {
  success: false;
  error_code?: string;
  message?: string;
}

export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
}

async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T | null> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  try {
    const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
    if (!res.ok) {
      try {
        const errorBody = await res.json();
        const errorCode = errorBody?.detail?.error_code || errorBody?.error_code;
        const errorMessage = errorBody?.detail?.message || errorBody?.message;
        if (errorCode) {
          console.error(`API error: ${res.status} ${errorCode} on ${path}`);
          return { success: false, error_code: errorCode, message: errorMessage } as T;
        }
      } catch {
        // Could not parse error body
      }
      console.error(`API error: ${res.status} ${res.statusText} on ${path}`);
      return null;
    }
    const text = await res.text();
    if (!text) return null as T;
    return JSON.parse(text) as T;
  } catch (err) {
    if (retry) {
      return apiFetch<T>(path, options, false);
    }
    console.error(`API fetch failed on ${path}:`, err);
    return null;
  }
}

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== null && v !== '',
  );
  if (entries.length === 0) return '';
  return '?' + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export function sendOtp(phone: string) {
  return apiFetch('/auth/send-otp', {
    method: 'POST',
    body: JSON.stringify({ phone }),
  });
}

export function verifyOtp(phone: string, otp: string) {
  return apiFetch('/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify({ phone, otp }),
  });
}

export function resendOtp(phone: string) {
  return apiFetch('/auth/resend-otp', {
    method: 'POST',
    body: JSON.stringify({ phone }),
  });
}

export function getMe(token: string) {
  return apiFetch('/auth/me', {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ── Farmers ───────────────────────────────────────────────────────────────────

export function createProfile(
  data: {
    name: string;
    age?: number;
    language?: string;
    village?: string;
    latitude?: number;
    longitude?: number;
  },
  token: string,
) {
  return apiFetch('/farmers/profile', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getFarmer(id: number, token: string) {
  return apiFetch(`/farmers/${id}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function updateFarmer(id: number, data: Record<string, unknown>, token: string) {
  return apiFetch(`/farmers/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function addCrop(
  farmerId: number,
  data: { crop_name: string; quantity: number; quantity_unit?: string },
  token: string,
) {
  return apiFetch(`/farmers/${farmerId}/crops`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getCrops(farmerId: number, token: string) {
  return apiFetch(`/farmers/${farmerId}/crops`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ── Location ──────────────────────────────────────────────────────────────────

export function reverseGeocode(latitude: number, longitude: number, language?: string) {
  return apiFetch(
    `/location/reverse-geocode${qs({ latitude, longitude, language })}`,
    { method: 'GET' },
  );
}

// ── Markets ───────────────────────────────────────────────────────────────────

export function getNearbyMarkets(
  latitude: number,
  longitude: number,
  radius_km?: number,
  crop?: string,
) {
  return apiFetch(
    `/markets/nearby${qs({ latitude, longitude, radius_km, crop })}`,
    { method: 'GET' },
  );
}

export function getMarket(marketId: number) {
  return apiFetch(`/markets/${marketId}`, { method: 'GET' });
}

export function compareMarkets(data: {
  crop: string;
  quantity: number;
  quantity_unit?: string;
  latitude: number;
  longitude: number;
}) {
  return apiFetch('/markets/compare', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Prices ────────────────────────────────────────────────────────────────────

export function getCurrentPrices(
  crop: string,
  marketId?: number,
  latitude?: number,
  longitude?: number,
  radius_km?: number,
) {
  return apiFetch(
    `/prices/current${qs({ crop, market_id: marketId, latitude, longitude, radius_km })}`,
    { method: 'GET' },
  );
}

export function getPriceTrend(crop: string, marketId: number, days?: number) {
  return apiFetch(
    `/prices/trend${qs({ crop, market_id: marketId, days })}`,
    { method: 'GET' },
  );
}

export function getPriceHistory(
  crop: string,
  marketId: number,
  start_date?: string,
  end_date?: string,
) {
  return apiFetch(
    `/prices/history${qs({ crop, market_id: marketId, start_date, end_date })}`,
    { method: 'GET' },
  );
}

// ── Profit ────────────────────────────────────────────────────────────────────

export function transportEstimate(data: {
  origin_latitude: number;
  origin_longitude: number;
  market_latitude: number;
  market_longitude: number;
  quantity: number;
  quantity_unit?: string;
}) {
  return apiFetch('/profit/transport-estimate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function calculateProfit(data: {
  crop: string;
  quantity: number;
  quantity_unit?: string;
  farmer_latitude: number;
  farmer_longitude: number;
}) {
  return apiFetch('/profit/calculate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Recommendations ───────────────────────────────────────────────────────────

export function sellWait(data: {
  crop: string;
  quantity: number;
  quantity_unit?: string;
  latitude: number;
  longitude: number;
  storage_available?: boolean;
  weather_risk?: string;
}) {
  return apiFetch('/recommendations/sell-wait', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export function chat(data: {
  message: string;
  language?: string;
  farmer_id?: number;
  crop?: string;
  quantity?: number;
  latitude?: number;
  longitude?: number;
}) {
  return apiFetch('/chat', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Weather ───────────────────────────────────────────────────────────────────

export function getWeather(latitude: number, longitude: number) {
  return apiFetch(
    `/weather${qs({ latitude, longitude })}`,
    { method: 'GET' },
  );
}

// ── Alerts ────────────────────────────────────────────────────────────────────

export interface AlertItem {
  id: string;
  type: string;
  title: string;
  body: string;
  severity: string;
  data_status: string;
  source: string;
}

export function getAlerts(params?: {
  language?: string;
  crop?: string;
  quantity?: number;
  latitude?: number;
  longitude?: number;
}) {
  return apiFetch<{
    alerts: AlertItem[];
    count: number;
    language: string;
    data_status: string;
  }>(`/alerts${qs({ ...params })}`, { method: 'GET' });
}

// ── Voice ─────────────────────────────────────────────────────────────────────

export function voiceTranscribe(data: {
  audio_data?: string;
  audio_url?: string;
  language?: string;
}) {
  return apiFetch('/voice/transcribe', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function voiceRespond(data: { text: string; language?: string }) {
  return apiFetch('/voice/respond', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export function voicePipeline(formData: FormData) {
  return apiFetch('/voice/pipeline', {
    method: 'POST',
    body: formData,
  });
}
