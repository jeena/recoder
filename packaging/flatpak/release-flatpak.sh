#!/usr/bin/env bash
set -euo pipefail

APP_ID="net.jeena.Recoder"
MANIFEST="${APP_ID}.yaml"
REPO_DIR="repo"
BRANCH="gh-pages"
WORKTREE_DIR="../../gh-pages"
PUBLISH_SUBDIR="flatpak-repo"
GPG_KEY_ID="1DF6570C929E2C186685046F0D6A8E36B9EE6177"

# Get version
VERSION=$(python3 -c 'import toml; print(toml.load("../../pyproject.toml")["project"]["version"])')

# Check metainfo.xml
if grep -q "<release version=\"$VERSION\"" ../../src/resources/net.jeena.Recoder.metainfo.xml; then
  echo "Version $VERSION found in metainfo."
else
  echo "Error: Version $VERSION not found in metainfo." >&2
  exit 1
fi

# Check git tag
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
  echo "Git tag v$VERSION exists."
else
  echo "Error: Git tag v$VERSION not found." >&2
  exit 1
fi

# Clean previous build
rm -rf build-dir "${REPO_DIR}"

# Build Flatpak and create signed repo
flatpak-builder --force-clean \
  --repo="${REPO_DIR}" \
  --default-branch=stable \
  --gpg-sign="${GPG_KEY_ID}" \
  build-dir "${MANIFEST}"

# Export public key into repo (also used below for flatpakref)
gpg --export --armor "${GPG_KEY_ID}" > "${REPO_DIR}/gpg.key"

# Clean up existing worktree if any
if [ -d "${WORKTREE_DIR}" ]; then
  echo "Removing existing worktree at ${WORKTREE_DIR}..."
  git worktree remove --force "${WORKTREE_DIR}"
  rm -rf "${WORKTREE_DIR}"
fi

# Prepare gh-pages worktree
git fetch origin "${BRANCH}" || true
git worktree add -B "${BRANCH}" "${WORKTREE_DIR}" "origin/${BRANCH}"

# Clear just the publish subdir inside the worktree
rm -rf "${WORKTREE_DIR:?}/${PUBLISH_SUBDIR}"
mkdir -p "${WORKTREE_DIR}/${PUBLISH_SUBDIR}"

# Copy repo files into the publish subdir
cp -r "${REPO_DIR}/"* "${WORKTREE_DIR}/${PUBLISH_SUBDIR}/"

# Generate .flatpakref inside worktree root
cat > "${WORKTREE_DIR}/${APP_ID}.flatpakref" <<EOF
[Flatpak Ref]
Title=Recoder
Name=${APP_ID}
Branch=stable
Url=https://jeena.github.io/recoder/${PUBLISH_SUBDIR}
IsRuntime=false
RuntimeRepo=https://flathub.org/repo/flathub.flatpakrepo
GPGKey=$(base64 -w0 < "${REPO_DIR}/gpg.key")
EOF

# Commit and push only the publish subdir and flatpakref
pushd "${WORKTREE_DIR}" > /dev/null
git add "${PUBLISH_SUBDIR}" "${APP_ID}.flatpakref"
git commit -m "Update Flatpak release to version ${VERSION}" || echo "No changes to commit"
git push origin "${BRANCH}"
popd > /dev/null

# Clean up worktree
git worktree remove "${WORKTREE_DIR}"

echo "✅ Release uploaded to GitHub Pages with GPG signing!"
