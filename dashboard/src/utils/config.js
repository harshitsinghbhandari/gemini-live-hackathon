// src/utils/config.js
export const getBackendUrl = () => {
    // If VITE_BACKEND_URL is set, use it.
    // Otherwise fallback to apiaegis.projectalpha.in
    return import.meta.env.VITE_BACKEND_URL || "https://apiaegis.projectalpha.in";
};
