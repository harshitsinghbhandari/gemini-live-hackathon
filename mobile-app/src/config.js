// src/config.js
export const getUserId = () => {
    return localStorage.getItem("aegis_user_id") || "";
};

export const CONFIG = {
    get USER_ID() { return getUserId(); },
    get DEVICE_ID() { return getUserId() ? `${getUserId()}-iphone` : "unknown-iphone"; },
    BACKEND_URL: import.meta.env.VITE_BACKEND_URL || "https://apiaegis.projectalpha.in",
    POLL_INTERVAL: 3000,
    AUTH_TIMEOUT: 30000,
};

console.log("Mobile App Config:", {
    BACKEND_URL: CONFIG.BACKEND_URL,
    DEVICE_ID: CONFIG.DEVICE_ID
});
