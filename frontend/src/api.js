/**
 * Smart Kisan — Axios API Client
 * Features:
 * - JWT access token injected into every request
 * - Auto refresh token rotation on 401 (silent re-login)
 * - Gemini API key forwarding for ML inference
 * - Unified error handling matching backend { success, data, error } schema
 */
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL
  ? (import.meta.env.VITE_API_URL.endsWith("/api")
    ? import.meta.env.VITE_API_URL
    : import.meta.env.VITE_API_URL + "/api")
  : "/api";

const api = axios.create({ baseURL: BASE_URL });

// ── Token storage helpers ──────────────────────────────────────────────────

const getAccessToken = () => localStorage.getItem("sk_token");
const getRefreshToken = () => localStorage.getItem("sk_refresh_token");
const getUserId = () => localStorage.getItem("sk_user_id");

const clearAuth = () => {
  ["sk_token", "sk_refresh_token", "sk_user_id", "sk_name", "sk_email", "sk_role"].forEach(
    (k) => localStorage.removeItem(k)
  );
};

// Track whether a refresh is in progress to queue concurrent 401 responses
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token);
  });
  failedQueue = [];
};

// ── Request Interceptor ────────────────────────────────────────────────────

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Forward Gemini API key for ML inference endpoints that need it
  const geminiKey = localStorage.getItem("sk_gemini_key");
  if (geminiKey) {
    config.headers["x-gemini-key"] = geminiKey.trim();
  }
  // Forward active user language preference (mr or en) for backend localization
  const lang = localStorage.getItem("sk-lang") || "mr";
  config.headers["x-language"] = lang;
  return config;
});

// ── Response Interceptor (Auto-refresh on 401) ────────────────────────────

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      getRefreshToken() &&
      getUserId()
    ) {
      if (isRefreshing) {
        // Queue up other 401s while refresh is in flight
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refreshToken: getRefreshToken(),
          userId: getUserId()
        });

        const { accessToken, refreshToken } = data.data;
        localStorage.setItem("sk_token", accessToken);
        localStorage.setItem("sk_refresh_token", refreshToken);

        api.defaults.headers.Authorization = `Bearer ${accessToken}`;
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;

        processQueue(null, accessToken);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearAuth();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Non-retryable 401 (e.g., no refresh token) → redirect to login
    if (error.response?.status === 401 && !originalRequest._retry) {
      clearAuth();
      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);

export default api;
