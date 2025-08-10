#!/usr/bin/env bash

set -e

echo "[DEBUG] Script started with arguments: $*"

# Parse arguments
PRODUCTION=false
for arg in "$@"; do
    echo "[DEBUG] Processing argument: $arg"
    if [[ "$arg" == "--production" ]]; then
        PRODUCTION=true
        echo "[DEBUG] Production flag set to true"
    fi
done

# Extract version from pyproject.toml
RAW_VERSION=$(grep -m1 '^version\s*=' pyproject.toml | sed -E 's/^version\s*=\s*"([^"]+)".*/\1/')

if [ -z "$RAW_VERSION" ]; then
    echo "[DEBUG] Error: Could not extract version from pyproject.toml"
    exit 1
fi

echo "[DEBUG] RAW_VERSION: $RAW_VERSION"

# Increment patch version
IFS='.' read -r MAJOR MINOR PATCH_EXTRA <<< "$RAW_VERSION"

echo "[DEBUG] MAJOR: $MAJOR"
echo "[DEBUG] MINOR: $MINOR"
echo "[DEBUG] PATCH_EXTRA: $PATCH_EXTRA"
echo "[DEBUG] RAW_VERSION: $RAW_VERSION"

# Handle possible pre-release suffixes in PATCH
PATCH=$(echo "$PATCH_EXTRA" | sed -E 's/[^0-9].*//')

echo "[DEBUG] PATCH (numeric part): $PATCH"

if [ -z "$PATCH" ]; then
    PATCH=0
    echo "[DEBUG] PATCH was empty, set to 0"
fi

PATCH=$((PATCH + 1))

echo "[DEBUG] PATCH incremented: $PATCH"

# Always use numeric version for pyproject.toml
NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

echo "[DEBUG] NEW_VERSION: $NEW_VERSION"

# Determine if production release
if [ "$PRODUCTION" = false ]; then
    printf "Is this a production release? [y/N]: "
    read IS_PROD
    echo "[DEBUG] User input for production: $IS_PROD"
    if [[ ! "$IS_PROD" =~ ^[Yy]$ ]]; then
        TAG_VERSION="${NEW_VERSION}a"
        RELEASE_TITLE="Release ${TAG_VERSION} - Alpha Release"
        RELEASE_NOTES="Alpha Release notes here"
        echo "[DEBUG] Alpha release selected"
    else
        TAG_VERSION="${NEW_VERSION}"
        RELEASE_TITLE="Release ${TAG_VERSION}"
        RELEASE_NOTES="Release notes here"
        echo "[DEBUG] Production release selected"
    fi
else
    TAG_VERSION="${NEW_VERSION}"
    RELEASE_TITLE="Release ${TAG_VERSION}"
    RELEASE_NOTES="Release notes here"
    echo "[DEBUG] Production flag was set, production release"
fi

echo "[DEBUG] TAG_VERSION: $TAG_VERSION"
echo "[DEBUG] RELEASE_TITLE: $RELEASE_TITLE"
echo "[DEBUG] RELEASE_NOTES: $RELEASE_NOTES"

# Update version in pyproject.toml (always numeric, no suffixes)
if ! grep -qE '^version\s*=' pyproject.toml; then
    echo "[DEBUG] Error: Could not find version line in pyproject.toml"
    exit 1
fi

# Use in-place editing with sed (compatible with both GNU and BSD/macOS sed)
if sed --version >/dev/null 2>&1; then
    # GNU sed
    echo "[DEBUG] Using GNU sed for in-place version update"
    sed -i -E "s/^version\s*=\s*\"[^\"]+\"/version = \"${NEW_VERSION}\"/" pyproject.toml
else
    # BSD/macOS sed
    echo "[DEBUG] Using BSD/macOS sed for in-place version update"
    # BSD/macOS sed: use a temp file for compatibility with some sed versions
    sed -E "s/^version\s*=\s*\"[^\"]+\"/version = \"${NEW_VERSION}\"/" pyproject.toml > pyproject.toml.tmp && mv pyproject.toml.tmp pyproject.toml
fi

# Double-check the version was updated
UPDATED_VERSION=$(grep -m1 '^version\s*=' pyproject.toml | sed -E 's/^version\s*=\s*"([^"]+)".*/\1/')
echo "[DEBUG] UPDATED_VERSION in pyproject.toml: $UPDATED_VERSION"
if [ "$UPDATED_VERSION" != "$NEW_VERSION" ]; then
    echo "[DEBUG] Error: Version update failed. pyproject.toml still has $UPDATED_VERSION, expected $NEW_VERSION"
    exit 1
fi

echo "[DEBUG] Updated version to $NEW_VERSION in pyproject.toml"

git add pyproject.toml

if ! git diff --cached --quiet; then
    echo "[DEBUG] Committing version bump"
    git commit -m "Release v${TAG_VERSION}"
else
    echo "[DEBUG] No changes to commit."
fi

echo "[DEBUG] Tagging release: v${TAG_VERSION}"
git tag -a "v${TAG_VERSION}" -m "$RELEASE_TITLE"
echo "[DEBUG] Pushing to origin main with tags"
git push origin main --follow-tags
echo "[DEBUG] Creating GitHub release"
gh release create "v${TAG_VERSION}" --title "$RELEASE_TITLE" --notes "$RELEASE_NOTES"
