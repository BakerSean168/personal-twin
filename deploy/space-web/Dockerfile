FROM php:8.3-cli-alpine

ARG SH3DJS_VERSION=7.5.2
ARG SH3DJS_SHA256=f48c45d6e9c94543ea1f01a003d72667846bd8bde7eb41fe58f675c806009931

RUN apk add --no-cache unzip

WORKDIR /app

COPY vendor/SweetHome3DJS-7.5.2.zip /tmp/sweethome3djs.zip

RUN echo "${SH3DJS_SHA256}  /tmp/sweethome3djs.zip" | sha256sum -c -     && unzip -q /tmp/sweethome3djs.zip -d /app     && rm /tmp/sweethome3djs.zip

COPY patch-index.php /tmp/patch-index.php
COPY writeData.php listHomes.php deleteHome.php /app/

RUN php /tmp/patch-index.php /app/index.html     && rm /tmp/patch-index.php     && mkdir -p /app/data

EXPOSE 8080

CMD ["php", "-S", "0.0.0.0:8080", "-t", "/app"]
