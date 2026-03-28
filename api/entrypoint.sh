#!/bin/sh
# Sync NANSEN_API_KEY env var into CLI config so CLI uses the same key
if [ -n "$NANSEN_API_KEY" ]; then
    mkdir -p /root/.nansen
    cat > /root/.nansen/config.json <<EOF
{
  "apiKey": "$NANSEN_API_KEY",
  "baseUrl": "https://api.nansen.ai"
}
EOF
fi

exec "$@"
