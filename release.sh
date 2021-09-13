#!/bin/bash

set -e

if command -v standard-version >/dev/null 2>&1; then
  cmd="standard-version"
elif command -v npx >/dev/null 2>&1; then
  cmd="npx standard-version"
else
  echo "error: please install npm package 'standard-version' or 'npx'"
  exit 1
fi

eval ${cmd} --dry-run ${@:1}

while true; do
	read -p "Publish this release? " yn
    case $yn in
        [Yy][Ee][Ss] ) break;;
        [Nn][Oo] ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

eval ${cmd} ${@:1}
git push --follow-tags
