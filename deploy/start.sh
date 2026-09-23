#!/usr/bin/env bash
set -euo pipefail

cd /home/root/projects/alkas
source venv/bin/activate

flask --app wsgi db upgrade
pm2 startOrRestart deploy/ecosystem.config.cjs --update-env
pm2 save

echo "Alkas is running on 127.0.0.1:4041"
