import axios from "axios";
export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const client = axios.create({ baseURL: API, withCredentials: true });
export const formatError = (e) => {
  const detail = e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const field = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : "field";
      const message = item?.msg || "is invalid";
      return `${String(field).replaceAll("_", " ")}: ${message}`;
    }).join(" • ");
  }
  if (detail && typeof detail.msg === "string") return detail.msg;
  return "Unable to save this event. Please check the form fields and try again.";
};