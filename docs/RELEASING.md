# Publishing Protocols

Hard rules for versioning and releasing FileSqueeze. The one-line summary:
**a published release is final — every shipped change bumps at least the
patch version, and every version bump ships with a documentation sweep.**

## 1. Published releases are final — no republishing

Once a version is published (a GitHub release tagged and the wheel attached),
it is never republished, retagged, deleted, or replaced under the same
version — no matter how small the problem. **Any change ships as a new
version with at least a PATCH bump** (`0.9.4` → `0.9.5`).

- The same-version republish of v0.9.4 (2026-10-12) was a deliberate one-off
  and is the last: it will never happen again.
- Consequence for the updater: a tree tagged `vX.Y.Z` must build exactly
  `filesqueeze-X.Y.Z-py3-none-any.whl` (the in-app updater verifies the
  wheel's filename and embedded metadata against the tag), and `main`'s
  `pyproject.toml` always declares the version the next release will carry.

## 2. One branch per minor version

When a minor version is released (`v1.0`, `v1.1`, …), create a branch from
`main` named after it (`v1.0`, `v1.1`, …). That branch owns the patch line
for that minor:

- PATCH releases (`1.0.1`, `1.0.2`, …) are committed on the minor version
  branch and released from it.
- A patch that also applies to other maintained minor lines is applied there
  too (cherry-pick the commit, adapt if the code has drifted).
- The current minor line (`v0.9`) follows the same rule.

## 3. Minor branches are linear

A minor branch's history must stay **linear**: PATCH commits are rebased on
each other (cherry-pick / rebase), never merge commits — each patch is one
reviewable unit that applies cleanly to the next branch. Feature work never
merges into a minor branch; features are developed on feature branches and
land on `main`, shipping in the next minor (or major) release.

## 4. main tracks the latest version

`main` is the tip of development for the newest minor line, and the newest
minor branch's released patches are always applied to it, so `main` carries
the latest version. Feature PRs target `main`.

## Release checklist (applies to every release)

1. **Bump PR** into the target branch (the newest minor branch for patches;
   `main` for features) setting `version` in `pyproject.toml` — at least a
   patch above anything ever published (rule 1), and the same version is
   never released twice. **The bump PR must include a documentation sweep**:
   verify the README, `docs/`, and installer/test documentation against
   everything shipping in this release, and fix stale or inaccurate content
   in the same PR — what the docs say must match what the release ships
   (compare claims against the code, not against memory).
2. **Tag the merge commit** (`v<full-version>`, e.g. `v0.9.4`) — not the
   branch tip at large.
3. **Build the wheel from that exact commit** and publish a **full
   (non-prerelease) GitHub release** with `filesqueeze-<version>-py3-none-any.whl`
   attached. Pre-releases are invisible to the in-app updater (GitHub's
   `/releases/latest` skips them), and the updater only offers a release
   whose wheel name matches the tag.
4. **Verify live**: `/releases/latest` serves the new tag, the wheel asset
   resolves, and (for a release a `v-1` install must adopt) a simulated
   older client's update check returns the new version with a wheel URL.
5. Tooling notes: pass release notes via `--notes-file` (backticks in
   `--notes` are shell-expanded), and pass the tag target as the **full**
   merge-commit SHA.
