// src/utils/config.js
export const getBackendUrl = () => {
    // If VITE_BACKEND_URL is set, use it.
    // Otherwise fallback to current origin (useful for containerized deployments on same port)
    // or localhost:8080 as a last resort.
    return import.meta.env.VITE_BACKEND_URL || window.location.origin;
};
