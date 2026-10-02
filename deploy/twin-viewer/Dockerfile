FROM node:22-alpine AS three
WORKDIR /vendor
RUN npm init -y >/dev/null 2>&1 \
    && npm install --ignore-scripts --no-audit --no-fund three@0.180.0

FROM nginx:1.27-alpine
COPY deploy/twin-viewer/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/twin-viewer/html/ /usr/share/nginx/html/
COPY --from=three /vendor/node_modules/three/build/ /usr/share/nginx/html/vendor/three/build/
COPY --from=three /vendor/node_modules/three/examples/jsm/ /usr/share/nginx/html/vendor/three/examples/jsm/
EXPOSE 8080
