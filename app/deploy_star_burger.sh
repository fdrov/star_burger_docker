#!/bin/bash

# strict mode
set -euo pipefail
IFS=$'\n\t'

cd /opt/star_burger_2/
: '
# git
if [[ $(git pull) == 'Already up to date.' ]]; then
    echo 'Git: already up to date'
    #exit
else
    echo 'Git: Pulling done.'
fi

# node
npm ci --dev > /dev/null 2>&1
node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url= | grep "Built in"

'

# django
source /opt/star_burger_2/venv/bin/activate
python -m pip install -r requirements.txt --quiet

source /opt/star_burger_2/.env

DATABASE_URL=$DATABASE_URL python manage.py migrate
DATABASE_URL=$DATABASE_URL python manage.py collectstatic --noinput --clear -v 0

# services
systemctl reload nginx.service
systemctl restart starburger.service

# rollbar 
commit_hash=$(git rev-parse --short HEAD)
commit_message=$(git log --format=%B -n 1 $commit_hash)
commit_author=$(git log --format='%an' -n 1 $commit_hash)
curl -s -H "X-Rollbar-Access-Token: $ROLLBAR_TOKEN" -H "Content-Type: application/json" -X POST 'https://api.rollbar.com/api/1/deploy' -d '{"environment": "production", "revision": "'$commit_hash'", "rollbar_name": "anton", "local_username": "'$commit_author'", "comment": "'$commit_message'", "status": "succeeded"}' > /dev/null

echo 'Deploying is finished'
