/**
 * Zustand store for authentication state management.
 */

import { create } from 'zustand';
import { api } from '@/lib/api';

const API_PREFIX = '/api/v1';
const TOKEN_KEY = 'darpan_token';
const USER_ID_KEY = 'darpan_user_id';

export interface AuthUser {
  user_id: string;
  email: string;
  display_name: string;
  sex: string | null;
  age: number | null;
  profile_completed: boolean;
  is_admin: boolean;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isInitialized: boolean;

  loginWithGoogle: (credential: string) => Promise<AuthUser>;
  updateProfile: (data: { display_name: string; sex: string; age: number }) => Promise<void>;
  logout: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isLoading: false,
  isInitialized: false,

  loginWithGoogle: async (credential: string) => {
    set({ isLoading: true });
    try {
      const response = await api.post<{
        access_token: string;
        token_type: string;
        user_id: string;
        email: string;
        display_name: string;
        profile_completed: boolean;
        is_admin: boolean;
      }>(`${API_PREFIX}/auth/google`, { credential });

      const { access_token, ...userData } = response;

      api.setToken(access_token);
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_ID_KEY, userData.user_id);

      const user: AuthUser = {
        user_id: userData.user_id,
        email: userData.email,
        display_name: userData.display_name,
        sex: null,
        age: null,
        profile_completed: userData.profile_completed,
        is_admin: userData.is_admin,
      };

      set({ user, token: access_token, isLoading: false });
      return user;
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  updateProfile: async (data) => {
    set({ isLoading: true });
    try {
      const response = await api.put<{
        user_id: string;
        email: string;
        display_name: string;
        sex: string | null;
        age: number | null;
        profile_completed: boolean;
        is_admin: boolean;
      }>(`${API_PREFIX}/auth/profile`, data);

      const user: AuthUser = {
        user_id: response.user_id,
        email: response.email,
        display_name: response.display_name,
        sex: response.sex,
        age: response.age,
        profile_completed: response.profile_completed,
        is_admin: response.is_admin,
      };

      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    api.setToken(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_ID_KEY);
    set({ user: null, token: null });
  },

  initialize: async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
    if (!token) {
      set({ isInitialized: true });
      return;
    }

    api.setToken(token);
    set({ token, isLoading: true });

    try {
      const user = await api.get<AuthUser>(`${API_PREFIX}/auth/me`);
      set({ user, isLoading: false, isInitialized: true });
    } catch {
      // Token invalid/expired — clear it
      api.setToken(null);
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_ID_KEY);
      set({ user: null, token: null, isLoading: false, isInitialized: true });
    }
  },
}));
