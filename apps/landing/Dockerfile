FROM nginx:alpine
COPY apps/landing/public /usr/share/nginx/html
COPY apps/landing/nginx.conf /etc/nginx/nginx.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
