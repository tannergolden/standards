<!--
title: '🧯 TROUBLESHOOTING'
description: 'Playbook for diagnosing common repository and pipeline issues.'
tags: [troubleshooting, playbook, operations, debugging]
category: docs
-->

<!-- markdownlint-disable MD041 -->
<div align="center">

# 🧯 TROUBLESHOOTING

<a name="top"></a>

**Accelerating recovery through precise diagnostic protocols and atomic checks.**

_Diagnostic precision. Deterministic parity. Fast recovery._

</div>

---

## 🚦 Phase 1: The 90-Second Triage

Before escalating, perform these atomic checks to eliminate 95% of common configuration drift.

1. **Verify Toolchain**: Run `nvm use` to align your local Node.js version with `.nvmrc`.
2. **Deterministic Install**: Run `rm -rf node_modules && make setup` to synchronize dependencies.
3. **CI Baseline**: Run `make lint` and `make test` to verify your local state matches CI requirements.
4. **Git Sanity**: Run `git fetch --all --prune` to ensure your remote trackers are up-to-date.

---

## 🔟 Common Pathological Symptoms

| Symptom                  | Probable Cause                | Immediate Resolution                                                                       |
| :----------------------- | :---------------------------- | :----------------------------------------------------------------------------------------- |
| **CI Red / Local Green** | Environmental drift.          | `nvm use`; sync lockfile with `npm ci`.                                                    |
| **Hook Bypass**          | Husky initialization failure. | `make setup`; `chmod +x .husky/*`.                                                         |
| **Blocked PR**           | Missing status checks.        | Update Branch Protection to match CI job names.                                            |
| **Merge Conflict**       | Divergent branch history.     | `git rebase origin/Development` & force-with-lease.                                        |
| **Emulator Failure**     | Port conflict.                | `lsof -i :8080` → `kill -9 <PID>`.                                                         |
| **Secret Leak**          | Credential committed to Git.  | Revoke key; follow [&#x1F512; Security & Secrets](Security-&-Secrets.md). |

---

## 🧰 Diagnostic Snapshot

Use these commands to generate a high-signal report for maintainers when seeking assistance.

```bash
echo "Node: $(node -v) | NPM: $(npm -v)"
git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD

make setup && make lint && make test && make build
```

---

## ⚙️ CI/CD & Pipeline Resolution

### Job Stuck in "Queued"

- **Environment Policy**: Check if the target environment (e.g., `Preview`) requires manual approval.
- **Concurrency**: Verify if another run is holding the concurrency lock for that branch.

### Playwright Launch Errors

If E2E tests fail on the Linux environment:

- **Dependency Missing**: Ensure `npx playwright install --with-deps` is in the CI workflow.
- **URL Connectivity**: Verify `PREVIEW_URL` is reachable and unauthenticated.

---

## 🔌 Local Environment & Emulators

### Freeing Occupied Ports

| Service       | Default Port | Resolve (macOS/Linux) |
| :------------ | :----------: | :-------------------- |
| **Firestore** |    `8080`    | `fuser -k 8080/tcp`   |
| **Auth**      |    `9099`    | `fuser -k 9099/tcp`   |
| **Functions** |    `5001`    | `fuser -k 5001/tcp`   |

---

## ⏪ Rollback & Incident Recovery

When minutes matter, follow the structured rollback path:

1. **Revert PR**: The fastest way to restore the `Development` branch to a known-green state.
2. **Deploy Last Tag**: Point your deployment pipeline to the `vX.Y.Z-1` tag to restore production.
3. **Back-merge**: Always ensure `Release` is back-merged to `Development` after a hotfix.

> [!CAUTION]
> Never attempt to "fix forward" a production outage without first restoring service. Roll back first, investigate second.

---

### 🔗 See also

> [!TIP]
> Every canonical guide is indexed in the [&#x1F4DA; Standards Index](https://github.com/tannergolden/standards/blob/Development/docs/README.md). If you rename or move a file, update every reference to it across the repository to prevent link drift.

---

<div align="center">

**Diagnostic precision. Fast resolution.**

[↑ Back to Top](#top)

<br />

Built with ❤️ by the Engineering Team. Distributed under the MIT License.

</div>
