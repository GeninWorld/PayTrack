"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, getBaseUrl } from "../lib/api";
import { clearAuth, getToken, getUser, saveToken, saveUser } from "../lib/storage";

const AuthContext = createContext({
  user: null,
  token: null,
  loading: true,
  login: async (_email, _password) => {},
  signup: async (_name, _email, _password) => {},
  logout: () => {},
  baseUrl: "",
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUser(getUser());
    setToken(getToken());
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await apiFetch(`/auth/dashboard/tenant/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    saveToken(data.access_token);
    saveUser(data.user);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  }, []);

  const signup = useCallback(async (name, email, password) => {
    const data = await apiFetch(`/auth/dashboard/tenant/signup`, {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    saveToken(data.access_token);
    saveUser(data.user);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    setToken(null);
  }, []);

  const value = useMemo(() => ({ user, token, loading, login, signup, logout, baseUrl: getBaseUrl() }), [user, token, loading, login, signup, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}


