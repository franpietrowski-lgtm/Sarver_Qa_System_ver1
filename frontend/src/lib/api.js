import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const TOKEN_KEY = "field-quality-token";

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
});

export const getStoredToken = () => localStorage.getItem(TOKEN_KEY);

export const setStoredToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    localStorage.removeItem(TOKEN_KEY);
    delete api.defaults.headers.common.Authorization;
  }
};

const bootToken = getStoredToken();
if (bootToken) {
  setStoredToken(bootToken);
}

export const loginRequest = async (email, password) => {
  const response = await api.post("/auth/login", { email, password });
  setStoredToken(response.data.token);
  return response.data;
};

export const logoutRequest = () => setStoredToken(null);

export const authGet = async (path, options = {}) => {
  const response = await api.get(path, options);
  return response.data;
};

export const authPost = async (path, payload, options = {}) => {
  const response = await api.post(path, payload, options);
  return response.data;
};

export const authPostForm = async (path, formData) => {
  const response = await api.post(path, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

export const authDownload = async (path) => api.get(path, { responseType: "blob" });

export const publicGet = async (path, options = {}) => {
  const response = await api.get(path, options);
  return response.data;
};

export const getApiOrigin = () => BACKEND_URL;