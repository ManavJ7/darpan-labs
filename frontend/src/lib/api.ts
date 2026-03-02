/**
 * API client for Darpan Labs backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface RequestConfig extends RequestInit {
  params?: Record<string, string>;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    return headers;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(path, this.baseUrl);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, value);
      });
    }

    return url.toString();
  }

  async request<T>(path: string, config: RequestConfig = {}): Promise<T> {
    const { params, ...fetchConfig } = config;
    const url = this.buildUrl(path, params);

    const response = await fetch(url, {
      ...fetchConfig,
      headers: {
        ...this.getHeaders(),
        ...fetchConfig.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));

      // On 401, clear stale token and redirect to login
      if (response.status === 401) {
        this.token = null;
        if (typeof window !== "undefined") {
          localStorage.removeItem("darpan_token");
          localStorage.removeItem("darpan_user_id");
          window.location.href = "/login";
        }
      }

      throw new ApiError(
        response.status,
        error.detail || "An error occurred",
        error
      );
    }

    return response.json();
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>(path, { method: "GET", params });
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(path: string, data?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Create and export singleton instance
export const api = new ApiClient(API_BASE_URL);

// Health check
export const checkHealth = () => api.get<HealthResponse>("/health");

// Types
export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  timestamp: string;
}

export { ApiError };
