import type { ApiResponse, AuthTokens } from '@ozhzo/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api/v1';

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private activeHomeId: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
      this.activeHomeId = localStorage.getItem('active_home_id');
    }
  }

  setTokens(tokens: AuthTokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;

    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', tokens.access_token);
      localStorage.setItem('refresh_token', tokens.refresh_token);
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

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = new Headers(options.headers);

    headers.set('Content-Type', 'application/json');

    if (this.accessToken) {
      headers.set(
        'Authorization',
        `Bearer ${this.accessToken}`
      );
    }

    if (this.activeHomeId) {
      headers.set('X-Home-ID', this.activeHomeId);
    }

    let response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });

    // Handle 401 token refresh retry
    if (
      response.status === 401 &&
      this.refreshToken &&
      !endpoint.includes('/auth/')
    ) {
      try {
        const refreshRes = await fetch(
          `${API_BASE_URL}/auth/refresh`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              refresh_token: this.refreshToken
            })
          }
        );

        const refreshData: ApiResponse<AuthTokens> =
          await refreshRes.json();

        if (refreshData.success) {
          this.setTokens(refreshData.data);

          headers.set(
            'Authorization',
            `Bearer ${refreshData.data.access_token}`
          );

          response = await fetch(
            `${API_BASE_URL}${endpoint}`,
            {
              ...options,
              headers
            }
          );
        } else {
          this.clearTokens();
        }
      } catch {
        this.clearTokens();
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

    if (!response.ok || (data && !data.success)) {
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

  post<T>(endpoint: string, body: unknown) {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  patch<T>(endpoint: string, body: unknown) {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body)
    });
  }

  delete<T>(endpoint: string) {
    return this.request<T>(endpoint, {
      method: 'DELETE'
    });
  }
}

export const apiClient = new ApiClient();
