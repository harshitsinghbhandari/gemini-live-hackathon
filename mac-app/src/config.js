// src/config.js
export const CONFIG = {
    USER_ID: localStorage.getItem("aegis_user_id") || import.meta.env.VITE_USER_ID || "harshitbhandari0318",
    HELPER_URL: import.meta.env.VITE_HELPER_URL || "http://localhost:8766",
    WS_URL: import.meta.env.VITE_WS_URL || "ws://localhost:8765",
    BACKEND_URL: import.meta.env.VITE_BACKEND_URL || "https://apiaegis.projectalpha.in",
    DASHBOARD_URL: import.meta.env.VITE_DASHBOARD_URL || "https://aegis.projectalpha.in",
    MOBILE_URL: import.meta.env.VITE_MOBILE_URL || "https://aegismobile.projectalpha.in",
};
