# SPDX-FileCopyrightText: 2026 Tanner Golden
# SPDX-License-Identifier: MIT
"""npm and crates.io publish without a stored token, and say why when they cannot.

Both registries trade the run's OIDC identity for a credential that lives
minutes, so a repository with a trusted publisher configured keeps no
registry secret at all. npm is removing direct publishing with a token, so
for npm this is the path that keeps working.

Each failure here is one a person meets once and cannot debug from a bare
401: npm too old to make the exchange, a trusted publisher naming the wrong
workflow file, a crate with no trusted publisher yet. Each must be named in
the run, with the fix. The crates.io token is minted, used and revoked in
one step, so it never reaches a later step or outlives the publish.

These run the shipped steps against a fake `node`, `npm`, `curl` and
`cargo`. Nothing touches a registry.
"""

from __future__ import annotations

import json
import os

import pytest
from conftest import load_yaml, workflow_on, workflow_step_shell

WORKFLOW = ".github/workflows/publish-package.yml"
CALLER = "o/r/.github/workflows/release.yml@refs/heads/main"


def fake(tmp_path, name: str, body: str) -> None:
    """Put an executable shell script called `name` on the test's PATH."""
    bindir = tmp_path / "_fakebin"
    bindir.mkdir(exist_ok=True)
    shim = bindir / name
    shim.write_text("#!/bin/bash\n" + body, encoding="utf-8")
    shim.chmod(0o755)


def env(tmp_path, **extra) -> dict:
    merged = {
        "PATH": f"{tmp_path / '_fakebin'}{os.pathsep}{os.environ.get('PATH', '')}",
        "GITHUB_REPOSITORY": "o/r",
        "GITHUB_WORKFLOW_REF": CALLER,
    }
    merged.update(extra)
    return merged


def versions(tmp_path, node: str, npm: str) -> None:
    fake(tmp_path, "node", f'echo "v{node}"\n')
    fake(tmp_path, "npm", f'echo "{npm}"\n')


class TestBothJobsCanAskForAnIdentity:
    @pytest.mark.parametrize("job", ["npm", "crates"])
    def test_the_job_grants_id_token(self, job):
        """Without it there is no OIDC identity to exchange, and no trusted publishing."""
        assert load_yaml(WORKFLOW)["jobs"][job]["permissions"].get("id-token") == "write"

    def test_pypi_says_it_needs_its_token(self):
        """PyPI refuses a reusable workflow's identity, so the token is not optional."""
        secrets = workflow_on(load_yaml(WORKFLOW))["workflow_call"]["secrets"]
        assert "Required" in secrets["PYPI_API_TOKEN"]["description"]
        assert "warehouse#11096" in secrets["PYPI_API_TOKEN"]["description"]


class TestNpmCredential:
    def shell(self):
        return workflow_step_shell(WORKFLOW, "npm", "credential")

    def test_a_token_is_used_and_flagged_for_retirement(self, run_shell, tmp_path):
        versions(tmp_path, "22.20.0", "10.9.3")
        result = run_shell(self.shell(), env=env(tmp_path, NPM_TOKEN="npm_x"))
        assert result.returncode == 0, result
        assert result.outputs == {"method": "token"}
        assert "January 2027" in result.output
        assert "release.yml" in result.output, "the warning must name the file to register"

    def test_without_a_token_it_publishes_through_trusted_publishing(self, run_shell, tmp_path):
        versions(tmp_path, "24.11.0", "11.6.2")
        result = run_shell(self.shell(), env=env(tmp_path, ACTIONS_ID_TOKEN_REQUEST_URL="https://oidc"))
        assert result.returncode == 0, result
        assert result.outputs == {"method": "trusted"}

    @pytest.mark.parametrize(
        ("node", "npm"),
        [("22.20.0", "10.9.3"), ("22.13.1", "11.6.2"), ("24.11.0", "11.5.0")],
        ids=["node-22-npm", "old-node", "npm-just-short"],
    )
    def test_an_npm_too_old_for_the_exchange_stops_before_the_build(self, run_shell, tmp_path, node, npm):
        versions(tmp_path, node, npm)
        result = run_shell(self.shell(), env=env(tmp_path, ACTIONS_ID_TOKEN_REQUEST_URL="https://oidc"))
        assert result.returncode == 1, result
        assert "npm too old for trusted publishing" in result.output
        assert "24.x" in result.output, "the error must name the fix"
        assert "method" not in result.outputs

    def test_the_first_version_that_can_is_enough(self, run_shell, tmp_path):
        versions(tmp_path, "22.14.0", "11.5.1")
        result = run_shell(self.shell(), env=env(tmp_path, ACTIONS_ID_TOKEN_REQUEST_URL="https://oidc"))
        assert result.outputs == {"method": "trusted"}, result

    def test_with_neither_it_fails_rather_than_skips(self, run_shell, tmp_path):
        versions(tmp_path, "24.11.0", "11.6.2")
        result = run_shell(self.shell(), env=env(tmp_path))
        assert result.returncode == 1, result
        assert "No npm credential" in result.output


PUBLISHING = {
    "DIST_TAG": "latest",
    "ACCESS": "public",
    "DRY_RUN": "false",
    "IS_PRIVATE": "false",
    "REGISTRY": "https://registry.npmjs.org",
}


class TestNpmPublish:
    def run(self, run_shell, tmp_path, said: str, code: int, method: str):
        fake(tmp_path, "npm", f"printf '%s\\n' {json.dumps(said)} >&2\nexit {code}\n")
        shell = workflow_step_shell(WORKFLOW, "npm", "publish")
        return run_shell(shell, env=env(tmp_path, METHOD=method, **PUBLISHING))

    def test_a_publish_that_works_passes(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, "+ pkg@1.0.0", 0, "trusted")
        assert result.returncode == 0, result
        assert result.outputs == {}

    def test_a_version_already_there_is_a_no_op(self, run_shell, tmp_path):
        """An anonymous probe cannot see a restricted package, so npm's refusal is the answer."""
        said = "npm error 403 403 Forbidden - PUT https://registry.npmjs.org/pkg - You cannot publish over the previously published versions: 1.0.0."
        result = self.run(run_shell, tmp_path, said, 1, "trusted")
        assert result.returncode == 0, result
        assert result.outputs == {"already": "true"}

    def test_a_refused_exchange_names_the_repository_and_the_file(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, "npm error code ENEEDAUTH", 1, "trusted")
        assert result.returncode == 1, result
        assert "Trusted publishing refused" in result.output
        assert "o/r and release.yml" in result.output

    def test_a_token_failure_gets_no_trusted_publishing_advice(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, "npm error code E401", 1, "token")
        assert result.returncode == 1, result
        assert "Trusted publishing refused" not in result.output

    def test_any_other_failure_still_fails(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, "npm error code E500", 1, "trusted")
        assert result.returncode == 1, result
        assert result.outputs == {}


class TestNpmRepositoryUrl:
    """npm refuses provenance, and a trusted publish, from a repository package.json does not name."""

    def run(self, run_shell, tmp_path, repository, **extra):
        package = {"name": "pkg", "version": "1.0.0"}
        if repository is not None:
            package["repository"] = repository
        (tmp_path / "package.json").write_text(json.dumps(package), encoding="utf-8")
        fake(tmp_path, "npm", "exit 1\n")  # `npm view`: not published yet
        settings = {"IS_PRIVATE": "false", "REGISTRY": "https://registry.npmjs.org", "NODE_AUTH_TOKEN": ""}
        settings.update(extra)
        shell = workflow_step_shell(WORKFLOW, "npm", "inspect")
        return run_shell(shell, env=env(tmp_path, **settings))

    @pytest.mark.parametrize(
        "repository",
        [
            "git+https://github.com/o/r.git",
            "https://github.com/O/R",
            "github:o/r",
            "o/r",
            "git@github.com:o/r.git",
            {"type": "git", "url": "git+ssh://git@github.com/o/r.git"},
        ],
    )
    def test_every_spelling_of_this_repository_passes(self, run_shell, tmp_path, repository):
        result = self.run(run_shell, tmp_path, repository)
        assert result.returncode == 0, result
        assert "repository.url does not match" not in result.output

    @pytest.mark.parametrize("repository", [None, "https://github.com/someone/else", "gitlab:o/r"])
    def test_another_repository_or_none_is_warned(self, run_shell, tmp_path, repository):
        result = self.run(run_shell, tmp_path, repository)
        assert result.returncode == 0, result
        assert "repository.url does not match" in result.output
        assert "git+https://github.com/o/r.git" in result.output, "the warning must give the value to set"

    def test_a_private_repository_publishing_with_a_token_is_not_checked(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, None, IS_PRIVATE="true", NODE_AUTH_TOKEN="npm_x")
        assert "repository.url does not match" not in result.output

    def test_another_registry_is_not_checked(self, run_shell, tmp_path):
        result = self.run(run_shell, tmp_path, None, REGISTRY="https://npm.pkg.github.com")
        assert "repository.url does not match" not in result.output


class TestCratesCredential:
    def shell(self):
        return workflow_step_shell(WORKFLOW, "crates", "🔑 Verify Credential")

    def test_an_oidc_identity_is_enough(self, run_shell, tmp_path):
        result = run_shell(self.shell(), env=env(tmp_path, ACTIONS_ID_TOKEN_REQUEST_URL="https://oidc"))
        assert result.returncode == 0, result

    def test_with_neither_it_fails_rather_than_skips(self, run_shell, tmp_path):
        result = run_shell(self.shell(), env=env(tmp_path))
        assert result.returncode == 1, result
        assert "No crates.io credential" in result.output


class TestCratesPublish:
    """The minted token is used for the publish and revoked however the step ends."""

    def run(self, run_shell, tmp_path, *, answer: str = '{"token":"cio_tp_minted"}', cargo: int = 0,
            revoked: str = "204", **extra):
        calls = tmp_path / "curl.log"
        fake(
            tmp_path,
            "curl",
            f"""echo "$*" >> "{calls}"
case "$*" in
  *audience=crates.io*) echo '{{"value":"github-jwt"}}' ;;
  *"-X POST"*) cat >> "{calls}"; echo >> "{calls}"; echo '{answer}' ;;
  *"-X DELETE"*) printf '%s' '{revoked}' ;;
  *) exit 99 ;;
esac
""",
        )
        fake(tmp_path, "cargo", f'echo "cargo $* token=${{CARGO_REGISTRY_TOKEN:-}}" >> "{calls}"\nexit {cargo}\n')
        settings = {
            "DRY_RUN": "false",
            "CARGO_REGISTRY_TOKEN": "",
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://oidc.example/token?x=1",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "runner-secret",
        }
        settings.update(extra)
        shell = workflow_step_shell(WORKFLOW, "crates", "🚀 Publish")
        result = run_shell(shell, env=env(tmp_path, **settings))
        log = calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
        return result, log

    def test_without_a_token_it_mints_one_and_publishes_with_it(self, run_shell, tmp_path):
        result, log = self.run(run_shell, tmp_path)
        assert result.returncode == 0, result
        assert any(line.startswith("cargo publish") and "token=cio_tp_minted" in line for line in log), log
        assert "::add-mask::cio_tp_minted" in result.stdout

    def test_it_sends_the_identity_in_the_body_not_on_the_command_line(self, run_shell, tmp_path):
        _, log = self.run(run_shell, tmp_path)
        assert '{"jwt":"github-jwt"}' in log
        assert not any("github-jwt" in line and "-X POST" in line for line in log)

    def test_the_token_is_revoked_after_the_publish(self, run_shell, tmp_path):
        _, log = self.run(run_shell, tmp_path)
        publish = next(i for i, line in enumerate(log) if line.startswith("cargo publish"))
        revoke = next(i for i, line in enumerate(log) if "-X DELETE" in line)
        assert revoke > publish, log
        assert "Authorization: Bearer cio_tp_minted" in log[revoke]

    def test_a_failed_publish_still_revokes_and_still_fails(self, run_shell, tmp_path):
        result, log = self.run(run_shell, tmp_path, cargo=101)
        assert result.returncode == 101, result
        assert any("-X DELETE" in line for line in log), log

    def test_a_failed_revocation_warns_but_does_not_undo_the_publish(self, run_shell, tmp_path):
        result, _ = self.run(run_shell, tmp_path, revoked="500")
        assert result.returncode == 0, result
        assert "Token not revoked" in result.output

    def test_a_refusal_quotes_crates_io_and_names_the_file(self, run_shell, tmp_path):
        refusal = json.dumps({"errors": [{"detail": "No Trusted Publishing config found for repository `o/r`."}]})
        result, log = self.run(run_shell, tmp_path, answer=refusal)
        assert result.returncode == 1, result
        assert "No Trusted Publishing config found" in result.output
        assert "o/r and release.yml" in result.output
        assert not any(line.startswith("cargo publish") for line in log)

    def test_an_unreadable_answer_still_fails_plainly(self, run_shell, tmp_path):
        result, _ = self.run(run_shell, tmp_path, answer="<html>bad gateway</html>")
        assert result.returncode == 1, result
        assert "no reason given" in result.output

    def test_a_stored_token_skips_the_exchange(self, run_shell, tmp_path):
        result, log = self.run(run_shell, tmp_path, CARGO_REGISTRY_TOKEN="cio_stored")
        assert result.returncode == 0, result
        assert log == ["cargo publish token=cio_stored"], log

    def test_a_dry_run_needs_no_credential_at_all(self, run_shell, tmp_path):
        result, log = self.run(run_shell, tmp_path, DRY_RUN="true")
        assert result.returncode == 0, result
        assert log == ["cargo publish --dry-run token="], log
