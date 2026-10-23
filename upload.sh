#!/usr/bin/env bash
# upload.sh — Upload a file to sendit.sh and output the fetch URL
set -euo pipefail

FILE="${1:-data/chapters/ch01/_kaggle_payload.zip}"

if [ ! -f "$FILE" ]; then
    echo "Error: File not found: $FILE" >&2
    exit 1
fi

NAME="$(basename "$FILE")"
echo "Uploading $NAME to https://sendit.sh..." >&2

RESPONSE=$(curl -sf "https://sendit.sh/$NAME" -T "$FILE")
URL=$(echo "$RESPONSE" | grep -o 'https://sendit\.sh/[^ ]*')

if [ -z "$URL" ]; then
    echo "Error: Failed to obtain upload URL from sendit.sh" >&2
    echo "$RESPONSE" >&2
    exit 1
fi

echo "$URL"
