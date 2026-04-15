FROM nginx:1.27-alpine

# Install certbot for Let's Encrypt, gettext for envsubst, openssl for self-signed certs
RUN apk add --no-cache certbot openssl gettext bash

COPY entrypoint.sh /entrypoint.sh
COPY templates/ /etc/nginx/templates/

RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
