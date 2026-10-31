#!/bin/sh
# Configuración en tiempo de ejecución: la misma imagen sirve en local y en Cloud Run.
echo "window.__CONFIG__ = { EXTRACTOR_VERTEX_URL: \"${EXTRACTOR_VERTEX_URL}\" };" > dist/config.js

exec ./node_modules/.bin/serve -s dist -l "${PORT}"
