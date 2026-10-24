FROM nginx:alpine

# Apply security upgrades to Alpine base packages
RUN apk update && apk upgrade --no-cache

# Copy frontend files
COPY . /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
