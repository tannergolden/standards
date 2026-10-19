#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
# =============================================================================
# Generate SBOM - a dependency inventory for any ecosystem
# =============================================================================
# A Software Bill of Materials is the list of what a build was actually made
# from. Attaching one to a release is what lets somebody answer "am I
# affected?" on the day a dependency is found vulnerable, without guessing
# from a lockfile they may not have.
#
# ECOSYSTEM-NATIVE GENERATORS DO NOT GENERALIZE. `npm sbom` covers npm and
# nothing else, so a repository that is not JavaScript gets no SBOM at all
# from it. Syft reads the manifests and lockfiles of every ecosystem it
# finds in a directory, which is the only approach that matches a standards
# repository claiming to be language agnostic.
#
# THE TOOL VERSION FLOATS BY DEFAULT, WHICH IS DELIBERATE AND NARROW. This
# binary only *describes* the build; it never touches the artifact being
# released, so a newer version cannot change what ships. Pinning it here
# instead would freeze every consuming repository on one version of the SBOM
# formats and the ecosystem catalogers, which ages badly and silently. Set
# SYFT_VERSION to pin it where reproducibility matters more.
#
# The download is integrity-checked against the checksums file published
# with the same release, so a corrupted or truncated fetch fails closed
# rather than producing a half-written binary.
#
# NON-FATAL BY DEFAULT. A missing SBOM should not sink a release that is
# otherwise good; it should be loud. SBOM_STRICT=true inverts that for
# anyone whose compliance posture needs the release to fail instead.
#
# Requires: SBOM_OUTPUT
# Optional: SBOM_FORMAT, SBOM_SOURCE, SYFT_VERSION, SBOM_STRICT, GH_TOKEN
# =============================================================================
set -euo pipefail

: "${SBOM_OUTPUT:?SBOM_OUTPUT is required}"

SBOM_FORMAT="${SBOM_FORMAT:-cyclonedx-json}"
SBOM_SOURCE="${SBOM_SOURCE:-dir:.}"
SYFT_VERSION="${SYFT_VERSION:-}"
SBOM_STRICT="$(printf '%s' "${SBOM_STRICT:-false}" | tr '[:upper:]' '[:lower:]')"

RELEASES_API='https://api.github.com/repos/anchore/syft/releases/latest'
DOWNLOAD_BASE='https://github.com/anchore/syft/releases/download'

emit() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf '%s\n' "$1" >> "$GITHUB_OUTPUT"
  fi
}

# Every abandonment path lands here, so the outputs are always defined and a
# caller never has to distinguish "the step did not run" from "it ran and
# produced nothing".
give_up() {
  emit 'generated=false'
  emit 'path='
  emit 'version='
  emit 'packages=0'
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    {
      echo "### 🧾 SBOM"
      echo ""
      echo "**Not generated.** $1"
    } >> "$GITHUB_STEP_SUMMARY"
  fi
  if [ "$SBOM_STRICT" = "true" ]; then
    echo "::error title=No SBOM::$1"
    exit 1
  fi
  echo "::warning title=No SBOM::$1 The release continues without one, which reduces its supply-chain provenance."
  exit 0
}

for tool in curl tar sha256sum jq; do
  if ! command -v "$tool" > /dev/null 2>&1; then
    give_up "'${tool}' is not available on this runner, so the generator could not be fetched."
  fi
done

case "$(uname -m)" in
  x86_64 | amd64) ARCH='amd64' ;;
  aarch64 | arm64) ARCH='arm64' ;;
  *) give_up "Unsupported runner architecture '$(uname -m)'; no matching generator is published." ;;
esac
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"

# An unauthenticated API call is rate limited per IP, which on a shared
# runner pool is a real failure mode rather than a theoretical one.
CURL_AUTH=()
if [ -n "${GH_TOKEN:-}" ]; then
  CURL_AUTH=(-H "Authorization: Bearer ${GH_TOKEN}")
fi

if [ -z "$SYFT_VERSION" ]; then
  echo "Resolving the current generator release..."
  RESOLVED=''
  if RESPONSE="$(curl -sSfL --retry 3 --retry-delay 2 --max-time 60 "${CURL_AUTH[@]}" "$RELEASES_API" 2> /dev/null)"; then
    RESOLVED="$(printf '%s' "$RESPONSE" | jq -r '.tag_name // empty')"
  fi
  if [ -z "$RESOLVED" ]; then
    give_up "Could not resolve the latest generator release. Set a version explicitly to remove the dependency on that lookup."
  fi
  SYFT_VERSION="$RESOLVED"
fi

# Accept 'v1.2.3' or '1.2.3' from a caller, since both look correct.
VERSION="${SYFT_VERSION#v}"
if ! printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
  give_up "Version '${SYFT_VERSION}' does not look like a release version."
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

TARBALL="syft_${VERSION}_${OS}_${ARCH}.tar.gz"
CHECKSUMS="syft_${VERSION}_checksums.txt"
BASE="${DOWNLOAD_BASE}/v${VERSION}"

echo "Fetching syft v${VERSION} for ${OS}/${ARCH}..."
if ! curl -sSfL --retry 3 --retry-delay 2 --max-time 180 -o "${TMP}/${TARBALL}" "${BASE}/${TARBALL}"; then
  give_up "Could not download ${TARBALL}. Check that v${VERSION} exists and publishes an asset for ${OS}/${ARCH}."
fi
if ! curl -sSfL --retry 3 --retry-delay 2 --max-time 60 -o "${TMP}/${CHECKSUMS}" "${BASE}/${CHECKSUMS}"; then
  give_up "Downloaded ${TARBALL} but not its checksums file, so its integrity could not be verified. Refusing to run an unverified binary."
fi

# Verified against the checksums published with the same release. This
# catches a corrupted or truncated download; it is not a substitute for
# trusting the publisher, which TLS and the release itself carry.
# `exit` inside awk rather than piping to `head`: with pipefail set, head
# closing the pipe early would signal awk and fail the whole command.
EXPECTED="$(awk -v want="$TARBALL" '$2 == want || $2 == "*" want { print $1; exit }' "${TMP}/${CHECKSUMS}")"
if [ -z "$EXPECTED" ]; then
  give_up "The checksums file for v${VERSION} lists no entry for ${TARBALL}. Refusing to run an unverified binary."
fi
ACTUAL="$(sha256sum "${TMP}/${TARBALL}" | awk '{ print $1 }')"
if [ "$EXPECTED" != "$ACTUAL" ]; then
  give_up "Checksum mismatch on ${TARBALL} (expected ${EXPECTED}, got ${ACTUAL}). Refusing to run it."
fi
echo "Checksum verified."

if ! tar -xzf "${TMP}/${TARBALL}" -C "$TMP" syft; then
  give_up "${TARBALL} does not contain a 'syft' binary, so nothing could be run."
fi
chmod +x "${TMP}/syft"

OUT_DIR="$(dirname "$SBOM_OUTPUT")"
mkdir -p "$OUT_DIR"

echo "Cataloging ${SBOM_SOURCE} as ${SBOM_FORMAT}..."
if ! "${TMP}/syft" scan "$SBOM_SOURCE" --output "${SBOM_FORMAT}=${SBOM_OUTPUT}" --quiet; then
  rm -f "$SBOM_OUTPUT"
  give_up "The generator could not catalog '${SBOM_SOURCE}' as '${SBOM_FORMAT}'. Check the source and the format name."
fi

if [ ! -s "$SBOM_OUTPUT" ]; then
  rm -f "$SBOM_OUTPUT"
  give_up "The generator produced an empty file, so there is nothing worth attaching."
fi

# CycloneDX calls them components and SPDX calls them packages. Counting
# both means the format stays the caller's choice.
PACKAGES="$(jq -r 'if has("components") then (.components | length) elif has("packages") then (.packages | length) else 0 end' "$SBOM_OUTPUT" 2> /dev/null || echo '0')"

# Zero is legitimate for a repository with no declared dependencies, and
# misleading for one that has them and was cataloged from the wrong place.
# It is called out rather than silently reported as a success.
if [ "$PACKAGES" = "0" ]; then
  echo "::notice title=SBOM lists nothing::The SBOM was generated but catalogs no packages. That is correct for a repository with no dependency manifests, and a sign of the wrong source otherwise."
fi

emit 'generated=true'
emit "path=${SBOM_OUTPUT}"
emit "version=${VERSION}"
emit "packages=${PACKAGES}"

echo "Wrote ${SBOM_OUTPUT} (${PACKAGES} package(s))."

if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
  {
    echo "### 🧾 SBOM"
    echo ""
    echo "| Field | Value |"
    echo "| :--- | :--- |"
    echo "| File | \`${SBOM_OUTPUT}\` |"
    echo "| Format | \`${SBOM_FORMAT}\` |"
    echo "| Source | \`${SBOM_SOURCE}\` |"
    echo "| Packages | ${PACKAGES} |"
    echo "| Generator | syft v${VERSION} |"
  } >> "$GITHUB_STEP_SUMMARY"
fi
