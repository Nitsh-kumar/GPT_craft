/// <reference types="vite/client" />

/**
 * api.ts
 * 
 * This is a wrapper around the native Fetch API.
 * It handles attaching the JWT token to every request and global error handling (like 401 Unauthorized).
 * 
 * SECURITY NOTE:
 * In a production environment, storing the JWT in memory and relying on an HttpOnly cookie
 * for the refresh token is the most secure approach against XSS attacks.
 * For simplicity in this implementation, we assume the token is managed by the AuthContext
 * and injected into this service.
 */

let currentToken: string | null = null;

export const setAuthToken = (token: string | null) => {
  currentToken = token;
};

export const getAuthToken = () => currentToken;

interface FetchOptions extends RequestInit {
  params?: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export const apiFetch = async <T>(endpoint: string, options: FetchOptions = {}): Promise<T> => {
  const { params, headers, ...customConfig } = options;

  // Construct URL with query parameters
  const url = new URL(endpoint, import.meta.env.VITE_API_BASE_URL || window.location.origin);
  if (params) {
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
  }

  // Set default headers and attach JWT if available
  const config: RequestInit = {
    ...customConfig,
    headers: {
      'Content-Type': 'application/json',
      ...(currentToken ? { Authorization: `Bearer ${currentToken}` } : {}),
      ...headers,
    },
  };

  try {
    const response = await fetch(url.toString(), config);

    // Handle HTTP errors
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        errorData = { message: response.statusText };
      }

      // Handle specific status codes globally if needed
      if (response.status === 401) {
        // Trigger a global logout event or token refresh logic
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }

      throw new ApiError(response.status, errorData.message || 'API Error', errorData);
    }

    // Return JSON response if content exists
    if (response.status !== 204) {
      return await response.json();
    }
    
    return {} as T;
  } catch (error) {
    // Network errors or aborted requests
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw error; // Let the caller handle aborts
    }
    throw new Error(error instanceof Error ? error.message : 'Network failure');
  }
};
