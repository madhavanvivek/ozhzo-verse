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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private activeHomeId: string | null = null;
  private refreshPromise: Promise<string | null> | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
      this.activeHomeId = localStorage.getItem('active_home_id');
    }
  }

  getAccessToken(): string | null {
    if (!this.accessToken && typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
    }
    return this.accessToken;
  }

  getRefreshToken(): string | null {
    if (!this.refreshToken && typeof window !== 'undefined') {
      this.refreshToken = localStorage.getItem('refresh_token');
    }
    return this.refreshToken;
  }

  getActiveHomeId(): string | null {
    if (!this.activeHomeId && typeof window !== 'undefined') {
      this.activeHomeId = localStorage.getItem('active_home_id');
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

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;

    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
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

  private handleUnauthorizedRedirect() {
    if (typeof window !== 'undefined') {
      const pathname = window.location.pathname;
      if (!pathname.startsWith('/login') && !pathname.startsWith('/register')) {
        window.location.href = '/login';
      }
    }
  }

  private async performTokenRefresh(): Promise<string | null> {
    const currentRefreshToken = this.getRefreshToken();
    if (!currentRefreshToken) {
      this.clearTokens();
      this.handleUnauthorizedRedirect();
      return null;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: currentRefreshToken
        })
      });

      if (!res.ok) {
        this.clearTokens();
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
        this.clearTokens();
        this.handleUnauthorizedRedirect();
        return null;
      }
    } catch {
      this.clearTokens();
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

    let response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });

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

        response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
      const errorMsg =
        data?.error?.message ||
        data?.detail ||
        (rawText ? `Server error (${response.status}): ${rawText}` : `Request failed with status ${response.status}`);
      throw new Error(errorMsg);
    }

    return data?.data as T;
  }

  get<T>(endpoint: string) {
    return this.request<T>(endpoint, {
      method: 'GET'
    });
  }

  post<T>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
  }

  patch<T>(endpoint: string, body?: unknown) {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body !== undefined ? JSON.stringify(body) : undefined
    });
  }

  delete<T>(endpoint: string) {
    return this.request<T>(endpoint, {
      method: 'DELETE'
    });
  }
}

export const apiClient = new ApiClient();
