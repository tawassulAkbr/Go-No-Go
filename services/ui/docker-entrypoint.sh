#!/bin/sh
set -eu
api_base="${API_BASE:-/api}"
printf 'window.__CONFIG__ = { API_BASE: "%s" };\n' "$api_base" > /tmp/config.js
