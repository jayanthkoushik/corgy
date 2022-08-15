#!/usr/bin/env sh
# Usage: ./release.sh <standard-version args>
# This script is used to publish a new version of the project.
# 'standard-version' or 'npx' must be installed.

set -e

if command -v standard-version >/dev/null 2>&1; then
  cmd="standard-version"
elif command -v npx >/dev/null 2>&1; then
  cmd="npx standard-version"
else
  echo "error: please install npm package 'standard-version' or 'npx'"
  exit 1
fi

echo "DRY RUN"
echo "======="
echo ""

eval ${cmd} --dry-run -a ${@:1}

echo ""
echo "======="
echo ""

while true; do
	read -p "Create release? " yn
    case $yn in
        [Yy][Ee][Ss] ) break;;
        [Nn][Oo] ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

eval ${cmd} -a ${@:1}

while true; do
	read -p "Publish release? " yn
    case $yn in
        [Yy][Ee][Ss] ) break;;
        [Nn][Oo] ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done

git push --follow-tags
