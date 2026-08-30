export interface AuthTokens {
  access_token: string;
  refresh_token?: string | null;
  token_type?: string;
  expires_in?: number;
  user_id?: string;
  phone_number?: string | null;
  email?: string | null;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  error?: {
    code?: string;
    message?: string;
    details?: any;
  };
  detail?: string;
}

export function resolveApiBaseUrl(): string {
  let base = (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    'https://ozhzo-api.onrender.com/api/v1'
  ).trim();

  // Strip trailing slashes
  while (base.endsWith('/')) {
    base = base.slice(0, -1);
  }

  // Ensure /api/v1 is present
  if (!base.endsWith('/api/v1') && !base.includes('/api/v1')) {
    base = `${base}/api/v1`;
  }
  return base;
}

export function buildApiUrl(endpoint: string): string {
  const base = resolveApiBaseUrl();
  let cleanEndpoint = (endpoint || '').trim();
  if (!cleanEndpoint.startsWith('/')) {
    cleanEndpoint = `/${cleanEndpoint}`;
  }
  return `${base}${cleanEndpoint}`;
}

export const API_BASE_URL = resolveApiBaseUrl();

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private activeHomeId: string | null = null;
  private refreshPromise: Promise<string | null> | null = null;
  private inFlightRequests: Map<string, Promise<any>> = new Map();
  private responseCache: Map<string, { timestamp: number; data: any }> = new Map();
  private readonly CACHE_TTL_MS = 10000; // 10 seconds for stable read queries

  constructor() {
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
      this.activeHomeId = localStorage.getItem('active_home_id');
    }
  }

  /**
   * Clear in-memory response cache.
   */
  clearCache(pattern?: string) {
    if (!pattern) {
      this.responseCache.clear();
      return;
    }
    for (const key of this.responseCache.keys()) {
      if (key.includes(pattern)) {
        this.responseCache.delete(key);
      }
    }
  }

  getAccessToken(): string | null {
    if (!this.accessToken && typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
    }
    return this.accessToken;
  }

  hasToken(): boolean {
    return !!this.getAccessToken();
  }

  getRefreshToken(): string | null {
    if (!this.refreshToken && typeof window !== 'undefined') {
      this.refreshToken = localStorage.getItem('refresh_token');
    }
    return this.refreshToken;
  }

  getActiveHomeId(): string | null {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('active_home_id');
      if (stored) {
        this.activeHomeId = stored;
        return stored;
      }
    }
    return this.activeHomeId;
  }

  setTokens(tokens: { access_token: string; refresh_token?: string | null }) {
    this.accessToken = tokens.access_token;
    if (tokens.refresh_token !== undefined && tokens.refresh_token !== null) {
      this.refreshToken = tokens.refresh_token;
    }

    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem('refresh_token', tokens.refresh_token);
      }
    }
  }

  /**
   * Complete session wipe: clears tokens, active home, cached states, and local/session storage.
   */
  clearSession() {
    this.accessToken = null;
    this.refreshToken = null;
    this.activeHomeId = null;
    this.clearCache();
    this.inFlightRequests.clear();

    if (typeof window !== 'undefined') {
      try {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('active_home_id');
        sessionStorage.clear();

        const keysToRemove: string[] = [];
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (
            key &&
            (key.startsWith('ozhzo_') ||
              key.includes('active_home') ||
              key.includes('user_profile') ||
              key.includes('home_cache'))
          ) {
            keysToRemove.push(key);
          }
        }
        keysToRemove.forEach((k) => localStorage.removeItem(k));
      } catch (e) {
        console.error('Error clearing session state:', e);
      }
    }
  }

  clearTokens() {
    this.clearSession();
  }

  setActiveHomeId(homeId: string | null) {
    this.activeHomeId = homeId;

    if (typeof window !== 'undefined') {
      if (homeId) {
        localStorage.setItem('active_home_id', homeId);
      } else {
        localStorage.removeItem('active_home_id');
      }
    }
  }

  /**
   * Deterministically validates active home against currently accessible homes.
   */
  resolveActiveHome(
    homes: Array<{ id?: string; home_id?: string; name?: string; role?: string }>
  ): string | null {
    if (!Array.isArray(homes) || homes.length === 0) {
      this.setActiveHomeId(null);
      return null;
    }

    const normalizedHomes = homes.map((h) => ({
      id: h.id || h.home_id || '',
      name: h.name || 'Home',
      role: h.role || 'MEMBER'
    }));

    const storedHomeId = this.getActiveHomeId();
    if (storedHomeId && normalizedHomes.some((h) => h.id === storedHomeId)) {
      return storedHomeId;
    }

    // Stale or missing Home ID -> Select first accessible home
    const firstHomeId = normalizedHomes[0].id;
    this.setActiveHomeId(firstHomeId);
    return firstHomeId;
  }

  /**
   * Retrieves and verifies a valid active Home ID for the currently authenticated user.
   * Never leaks or returns a stale Home ID belonging to another user.
   */
  async getValidActiveHome(): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    try {
      const homes = await this.get<Array<{ id: string; name?: string; role?: string }>>('/homes');
      return this.resolveActiveHome(homes || []);
    } catch (err: any) {
      console.warn('Unable to validate user home memberships:', err?.message);
      return null;
    }
  }

  private handleUnauthorizedRedirect() {
    if (typeof window !== 'undefined') {
      const pathname = window.location.pathname;
      if (!pathname.startsWith('/login') && !pathname.startsWith('/register')) {
        this.clearSession();
        window.location.href = '/login';
      }
    }
  }

  private async performTokenRefresh(): Promise<string | null> {
    const currentRefreshToken = this.getRefreshToken();
    if (!currentRefreshToken) {
      this.clearSession();
      this.handleUnauthorizedRedirect();
      return null;
    }

    try {
      const refreshUrl = buildApiUrl('/auth/refresh');
      const res = await fetch(refreshUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: currentRefreshToken
        })
      });

      if (!res.ok) {
        this.clearSession();
        this.handleUnauthorizedRedirect();
        return null;
      }

      const json: ApiResponse<AuthTokens> = await res.json();
      if (json.success && json.data?.access_token) {
        this.setTokens({
          access_token: json.data.access_token,
          refresh_token: json.data.refresh_token || currentRefreshToken
        });
        return json.data.access_token;
      } else {
        this.clearSession();
        this.handleUnauthorizedRedirect();
        return null;
      }
    } catch {
      this.clearSession();
      this.handleUnauthorizedRedirect();
      return null;
    }
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = new Headers(options.headers);

    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const token = this.getAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const url = buildApiUrl(endpoint);
    let response: Response;
    try {
      response = await fetch(url, {
        ...options,
        headers
      });
    } catch (networkErr: any) {
      console.error(`Network fetch failed for ${url}:`, networkErr);
      throw new Error(networkErr?.message || 'Failed to connect to API server. Please check your connection.');
    }

    // Handle 401 token refresh retry (avoid loop on auth endpoints)
    if (response.status === 401 && !endpoint.includes('/auth/')) {
      if (!this.refreshPromise) {
        this.refreshPromise = this.performTokenRefresh().finally(() => {
          this.refreshPromise = null;
        });
      }

      const newAccessToken = await this.refreshPromise;

      if (newAccessToken) {
        const retryHeaders = new Headers(options.headers);
        retryHeaders.set('Content-Type', 'application/json');
        retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);

        response = await fetch(url, {
          ...options,
          headers: retryHeaders
        });
      } else {
        throw new Error('Invalid or expired session. Please sign in again.');
      }
    }

    const contentType = response.headers.get('content-type') || '';
    let data: any = null;
    let rawText = '';

    if (contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    } else {
      try {
        rawText = await response.text();
      } catch {
        rawText = '';
      }
    }

    if (!response.ok || (data && data.success === false)) {
      let errorMsg = 'An unexpected error occurred';
      if (data?.error?.message && typeof data.error.message === 'string') {
        errorMsg = data.error.message;
      } else if (typeof data?.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data?.detail)) {
        errorMsg = data.detail.map((d: any) => d.msg || d.message || (typeof d === 'string' ? d : JSON.stringify(d))).join(', ');
      } else if (data?.detail && typeof data.detail === 'object') {
        errorMsg = data.detail.message || data.detail.msg || JSON.stringify(data.detail);
      } else if (data?.message && typeof data.message === 'string') {
        errorMsg = data.message;
      } else if (rawText) {
        errorMsg = `Server error (${response.status}): ${rawText}`;
      } else {
        errorMsg = `Request failed with status ${response.status}`;
      }

      // Handle 403 Home Membership Error: clear stale home selection
      if (
        response.status === 403 &&
        (errorMsg.toLowerCase().includes('not an active member') ||
          errorMsg.includes('HOME_NOT_MEMBER') ||
          errorMsg.includes('Not an active member of this home'))
      ) {
        this.setActiveHomeId(null);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('stale-home-cleared'));
          window.dispatchEvent(new CustomEvent('home-changed'));
        }
      }

      throw new Error(errorMsg);
    }

    if (data && typeof data === 'object' && 'data' in data && data.data !== undefined) {
      return data.data as T;
    }

    return data as T;
  }

  get<T>(endpoint: string, options?: { skipCache?: boolean }): Promise<T> {
    const token = this.getAccessToken() || '';
    const cleanEndpoint = endpoint.trim().split('?')[0];
    const normalizedEndpoint = cleanEndpoint.startsWith('/') ? cleanEndpoint : `/${cleanEndpoint}`;
    const cacheKey = `${normalizedEndpoint}::${token}`;
    const isCacheable = (normalizedEndpoint === '/users/me' || normalizedEndpoint === '/homes') && !options?.skipCache;

    // 1. Return fresh cached response if available
    if (isCacheable) {
      const cached = this.responseCache.get(cacheKey);
      if (cached && (Date.now() - cached.timestamp < this.CACHE_TTL_MS)) {
        return Promise.resolve(cached.data as T);
      }
    }

    // 2. Coalesce concurrent in-flight requests
    const existingInFlight = this.inFlightRequests.get(cacheKey);
    if (existingInFlight) {
      return existingInFlight as Promise<T>;
    }

    const requestPromise = this.request<T>(endpoint, { method: 'GET' })
      .then((data) => {
        if (isCacheable) {
          this.responseCache.set(cacheKey, { timestamp: Date.now(), data });
        }
        return data;
      })
      .finally(() => {
        this.inFlightRequests.delete(cacheKey);
      });

    this.inFlightRequests.set(cacheKey, requestPromise);
    return requestPromise;
  }

  post<T>(endpoint: string, body?: unknown) {
    this.clearCache();
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
  }

  patch<T>(endpoint: string, body?: unknown) {
    this.clearCache();
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
  }

  delete<T>(endpoint: string) {
    this.clearCache();
    return this.request<T>(endpoint, {
      method: 'DELETE'
    });
  }
}

export const apiClient = new ApiClient();

