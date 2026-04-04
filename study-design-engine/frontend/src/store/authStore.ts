import { create } from "zustand";
import { googleLogin, type UserResponse } from "@/lib/authApi";

interface AuthStore {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;

  loginWithGoogle: (googleToken: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isLoading: true,

  loginWithGoogle: async (googleToken: string) => {
    const res = await googleLogin(googleToken);
    localStorage.setItem("auth_token", res.access_token);
    localStorage.setItem("auth_user", JSON.stringify(res.user));
    set({ user: res.user, token: res.access_token });
  },

  logout: () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    set({ user: null, token: null });
  },

  loadFromStorage: () => {
    const token = localStorage.getItem("auth_token");
    const userStr = localStorage.getItem("auth_user");

    if (token && userStr) {
      try {
        // Check if JWT is expired (decode payload without verification)
        const payload = JSON.parse(atob(token.split(".")[1]));
        if (payload.exp * 1000 > Date.now()) {
          set({ user: JSON.parse(userStr), token, isLoading: false });
          return;
        }
      } catch {
        // Invalid token — fall through to clear
      }
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
    }
    set({ user: null, token: null, isLoading: false });
  },
}));
