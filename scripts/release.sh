#!/usr/bin/env bash

set -e

# Parse arguments
PRODUCTION=false
for arg in "$@"; do
    if [[ "$arg" == "--production" ]]; then
        PRODUCTION=true
    fi
done

# Extract version from pyproject.toml
RAW_VERSION=$(grep -m1 '^version\s*=' pyproject.toml | sed -E "s/version\s*=\s*\"([^\"]+)\"/\1/")

if [ -z "$RAW_VERSION" ]; then
    echo "Error: Could not extract version from pyproject.toml"
    exit 1
fi

# Increment patch version
IFS='.' read -r MAJOR MINOR PATCH_EXTRA <<< "$RAW_VERSION"

# Handle possible pre-release suffixes in PATCH
PATCH=$(echo "$PATCH_EXTRA" | sed -E 's/[^0-9].*//')
# EXTRA=$(echo "$PATCH_EXTRA" | sed -E 's/^[0-9]+//')

PATCH=$((PATCH + 1))

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

# Determine if production release
if [ "$PRODUCTION" = false ]; then
    printf "Is this a production release? [y/N]: "
    read IS_PROD
    if [[ ! "$IS_PROD" =~ ^[Yy]$ ]]; then
        NEW_VERSION="${NEW_VERSION}a"
        RELEASE_TITLE="Release v${NEW_VERSION} - Alpha Release"
        RELEASE_NOTES="Alpha Release notes here"
    else
        RELEASE_TITLE="Release v${NEW_VERSION}"
        RELEASE_NOTES="Release notes here"
    fi
else
    RELEASE_TITLE="Release v${NEW_VERSION}"
    RELEASE_NOTES="Release notes here"
fi

# Update version in pyproject.toml
sed -i.bak -E "s/^version\s*=\s*\"[^\"]+\"/version = \"${NEW_VERSION}\"/" pyproject.toml

git add .
git commit -m "Release v${NEW_VERSION}"
git tag -a "v${NEW_VERSION}" -m "$RELEASE_TITLE"
git push origin main --follow-tags
gh release create "v${NEW_VERSION}" --title "$RELEASE_TITLE" --notes "$RELEASE_NOTES"
