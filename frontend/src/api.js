import axios from "axios";
export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const client = axios.create({ baseURL: API, withCredentials: true });
export const formatError = (e) => { const d=e?.response?.data?.detail; return typeof d === "string" ? d : "Something went wrong. Please try again."; };