#!/bin/bash

# Start the API server in the background (note the .cjs extension)
node /app/api-server.cjs &

# Start nginx in the foreground
nginx -g "daemon off;" 