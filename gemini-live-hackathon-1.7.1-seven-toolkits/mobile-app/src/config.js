// src/config.js
export const CONFIG = {
    BACKEND_URL: import.meta.env.VITE_BACKEND_URL || "https://apiaegis.projectalpha.in",
    POLL_INTERVAL: 3000,
    AUTH_TIMEOUT: 30000,
    DEVICE_ID: import.meta.env.VITE_DEVICE_ID || "harshit-iphone" // Default device ID per specification
};

console.log("Mobile App Config:", {
    BACKEND_URL: CONFIG.BACKEND_URL,
    DEVICE_ID: CONFIG.DEVICE_ID
});
