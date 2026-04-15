#!/bin/bash
# EveryStore management helper

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

SECRETS_FILE="/app/secrets/admin.env"

_read_secrets() {
    docker exec everystore-app cat "$SECRETS_FILE" 2>/dev/null
}

_get_public_ip() {
    curl -sf --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4 \
        || curl -sf --max-time 3 https://api.ipify.org \
        || echo "YOUR_SERVER_IP"
}

cmd_admin() {
    SECRETS=$(_read_secrets)
    if [ -z "$SECRETS" ]; then
        echo -e "${RED}Error: could not read admin credentials. Is the container running?${RESET}"
        exit 1
    fi

    eval "$SECRETS"
    IP=$(_get_public_ip)

    echo ""
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║                  EveryStore — Admin Access                      ║${RESET}"
    echo -e "${BOLD}${CYAN}╠══════════════════════════════════════════════════════════════════╣${RESET}"
    printf "${BOLD}${CYAN}║${RESET}  URL:       ${GREEN}https://%s:%s/%s/${RESET}\n" "$IP" "$ADMIN_PORT" "$ADMIN_URL_PATH"
    printf "${BOLD}${CYAN}║${RESET}  Username:  ${BOLD}admin${RESET}\n"
    printf "${BOLD}${CYAN}║${RESET}  Password:  ${BOLD}%s${RESET}\n" "$ADMIN_PASSWORD"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    echo -e "${YELLOW}Make sure port ${ADMIN_PORT} is open in your AWS Security Group.${RESET}"
    echo ""
}

cmd_change_port() {
    SECRETS=$(_read_secrets)
    if [ -z "$SECRETS" ]; then
        echo -e "${RED}Error: could not read admin credentials. Is the container running?${RESET}"
        exit 1
    fi
    eval "$SECRETS"

    echo -e "Current admin port: ${BOLD}${ADMIN_PORT}${RESET}"
    read -rp "$(echo -e "${BOLD}Enter new port (1024–65535) or press Enter to auto-generate: ${RESET}")" NEW_PORT

    if [ -z "$NEW_PORT" ]; then
        NEW_PORT=$(python3 -c "import random; print(random.randint(10000, 65000))")
        echo -e "Auto-generated port: ${BOLD}${NEW_PORT}${RESET}"
    fi

    if ! [[ "$NEW_PORT" =~ ^[0-9]+$ ]] || [ "$NEW_PORT" -lt 1024 ] || [ "$NEW_PORT" -gt 65535 ]; then
        echo -e "${RED}Invalid port. Must be a number between 1024 and 65535.${RESET}"
        exit 1
    fi

    # Update secrets file inside the container volume
    docker exec everystore-app bash -c "
        source '${SECRETS_FILE}'
        printf 'ADMIN_PORT=%q\nADMIN_PASSWORD=%q\nADMIN_URL_PATH=%q\n' \
            '${NEW_PORT}' \"\$ADMIN_PASSWORD\" \"\$ADMIN_URL_PATH\" > '${SECRETS_FILE}'
    "

    echo -e "${GREEN}Port updated to ${NEW_PORT}. Restarting containers...${RESET}"
    docker compose restart everystore-app everystore-nginx

    IP=$(_get_public_ip)
    echo ""
    echo -e "${GREEN}Done. New admin URL:${RESET}"
    echo -e "  ${BOLD}https://${IP}:${NEW_PORT}/${ADMIN_URL_PATH}/${RESET}"
    echo ""
    echo -e "${YELLOW}Remember to update your AWS Security Group:${RESET}"
    echo -e "  - Remove old port ${ADMIN_PORT}"
    echo -e "  - Add new port ${NEW_PORT}"
    echo ""
}

cmd_help() {
    echo ""
    echo -e "${BOLD}Usage:${RESET} ./manage.sh <command>"
    echo ""
    echo -e "${BOLD}Commands:${RESET}"
    echo "  admin          Show admin panel URL and credentials"
    echo "  change-port    Change the admin panel port"
    echo "  help           Show this help message"
    echo ""
}

case "${1:-help}" in
    admin)        cmd_admin ;;
    change-port)  cmd_change_port ;;
    help|--help)  cmd_help ;;
    *)
        echo -e "${RED}Unknown command: $1${RESET}"
        cmd_help
        exit 1
        ;;
esac
