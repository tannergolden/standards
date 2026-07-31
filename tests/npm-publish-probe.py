# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""The already-published probe must read the registry as the publisher.

`🔎 Inspect Package` decides whether the version is already on the registry
so a re-run reports a no-op instead of failing with a 403 at the end. It ran
`npm view` in a step whose `env:` carried only `EXPECTED` and `RELEASE_TAG`;
`NODE_AUTH_TOKEN` was set on the later publish step alone.

So the probe was unauthenticated even though `actions/setup-node` had
already written an `.npmrc` expecting a token. For a scoped package
published with `--access restricted`, or any private or self-hosted registry
named by `npm-registry`, an anonymous read 404s and the step recorded
`published=false`.

Which means the idempotence the step exists to provide never engaged: a
re-run after an unrelated failure always reached `npm publish` again, and
npm rejected the duplicate version. The check was there, and it was reading
as a stranger.
"""

from __future__ import annotations

from conftest import load_yaml

WORKFLOW = ".github/workflows/publish-package.yml"


def step(step_id: str) -> dict:
    steps = load_yaml(WORKFLOW)["jobs"]["npm"]["steps"]
    return next(s for s in steps if s.get("id") == step_id or s.get("name") == step_id)


class TestTheProbeIsAuthenticated:
    def test_it_carries_a_registry_token(self):
        """The defect: it read the registry anonymously."""
        env = step("inspect").get("env") or {}
        assert "NODE_AUTH_TOKEN" in env, (
            "the already-published probe runs unauthenticated, so a restricted or "
            "private package always reads as not published and every re-run republishes"
        )

    def test_it_is_the_same_secret_the_publish_step_uses(self):
        probe = (step("inspect").get("env") or {})["NODE_AUTH_TOKEN"]
        publish = (step("🚀 Publish").get("env") or {})["NODE_AUTH_TOKEN"]
        assert probe == publish, (
            f"the probe reads as {probe!r} and the publish writes as {publish!r}; "
            "they must be the same identity or the probe answers a different question"
        )


class TestTheProbeStillDoesItsJob:
    def test_it_records_both_outcomes(self):
        shell = step("inspect")["run"]
        assert "published=true" in shell
        assert "published=false" in shell

    def test_the_publish_step_is_gated_on_it(self):
        publish = step("🚀 Publish")
        assert "steps.inspect.outputs.published" in str(publish.get("if")), (
            "the publish step no longer consults the probe, so authenticating it "
            "would protect nothing"
        )
