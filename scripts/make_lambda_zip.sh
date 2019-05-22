#!/bin/bash

set -euo pipefail

# current directory of script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

cd $DIR/../numerai

rm -f lambda.zip
npm install
zip -r lambda.zip exports.js node_modules/
