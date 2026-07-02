"""Git 变更检测与版本发布逻辑。"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

PROJECTS: dict[str, dict[str, str]] = {
    "project-a": {"dir": "project-a", "tag_prefix": "a"},
    "project-b": {"dir": "project-b", "tag_prefix": "b"},
}


@dataclass
class ReleaseResult:
    project: str
    changed: bool
    released: bool
    version: str | None = None
    tag: str | None = None
    changed_files: list[str] | None = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "changed": self.changed,
            "released": self.released,
            "version": self.version,
            "tag": self.tag,
            "changed_files": self.changed_files or [],
            "message": self.message,
        }


def _run_git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"git {' '.join(args)} 失败: {stderr}")
    return result.stdout.strip()


def detect_changes(project_dir: str) -> tuple[bool, list[str]]:
    """检测指定子项目在本次 push 中是否有变更。"""
    event_name = os.environ.get("GITHUB_EVENT_NAME", "push")

    if event_name == "pull_request":
        base_sha = os.environ["GITHUB_BASE_SHA"]
        head_sha = os.environ["GITHUB_SHA"]
        diff_output = _run_git("diff", "--name-only", base_sha, head_sha)
    else:
        before_sha = os.environ.get("GITHUB_EVENT_BEFORE", "")
        after_sha = os.environ.get("GITHUB_SHA", "HEAD")

        if not before_sha or before_sha == "0" * 40:
            diff_output = _run_git("diff", "--name-only", "HEAD~1", "HEAD", check=False)
        else:
            diff_output = _run_git("diff", "--name-only", before_sha, after_sha)

    prefix = f"{project_dir}/"
    changed_files = [
        line for line in diff_output.splitlines() if line.startswith(prefix)
    ]
    return bool(changed_files), changed_files


def _next_version(project_dir: str, tag_prefix: str) -> tuple[str, str, str]:
    """计算下一个版本号并返回 (version, tag)。"""
    version_file = REPO_ROOT / project_dir / "VERSION"
    tag_pattern = f"{tag_prefix}-v*"

    latest_tag = _run_git("tag", "-l", tag_pattern, "--sort=-v:refname", check=False)
    latest_tag = latest_tag.splitlines()[0] if latest_tag else ""

    if not latest_tag:
        version = version_file.read_text(encoding="utf-8").strip()
        message = f"首次发布，使用 VERSION 文件中的版本: {version}"
    else:
        current = latest_tag.removeprefix(f"{tag_prefix}-v")
        major, minor, patch = current.split(".")
        version = f"{major}.{minor}.{int(patch) + 1}"
        message = f"基于 {latest_tag} 递增 patch 版本 -> {version}"

    new_tag = f"{tag_prefix}-v{version}"
    return version, new_tag, message


def release_project(project_key: str, force: bool = False) -> ReleaseResult:
    """检测变更并发布：更新 VERSION、提交、打 tag。"""
    if project_key not in PROJECTS:
        raise ValueError(f"未知项目: {project_key}")

    config = PROJECTS[project_key]
    project_dir = config["dir"]
    tag_prefix = config["tag_prefix"]

    changed, changed_files = detect_changes(project_dir)
    if not changed and not force:
        return ReleaseResult(
            project=project_key,
            changed=False,
            released=False,
            changed_files=changed_files,
            message=f"{project_key} 无变更，跳过发布",
        )

    version, new_tag, version_message = _next_version(project_dir, tag_prefix)
    version_file = REPO_ROOT / project_dir / "VERSION"
    version_file.write_text(f"{version}\n", encoding="utf-8")

    _run_git("add", str(version_file.relative_to(REPO_ROOT)))
    _run_git(
        "-c", "user.name=github-actions[bot]",
        "-c", "user.email=github-actions[bot]@users.noreply.github.com",
        "commit",
        "-m", f"chore({tag_prefix}): bump version to {version} [skip ci]",
    )
    _run_git("tag", "-a", new_tag, "-m", f"Release {tag_prefix} v{version}")

    return ReleaseResult(
        project=project_key,
        changed=True,
        released=True,
        version=version,
        tag=new_tag,
        changed_files=changed_files,
        message=f"已创建 tag: {new_tag}（{version_message}）",
    )
