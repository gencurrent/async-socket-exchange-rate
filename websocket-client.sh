SERVER_HOST="${SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${SERVER_PORT:-8080}"
URL="ws://$SERVER_HOST:$SERVER_PORT/"
echo "Connecting to $URL"
websocat $URL