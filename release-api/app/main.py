"""Release API：两个项目各一个 HTTP 接口。"""

from fastapi import FastAPI, HTTPException, Query

from app.services.git_release import PROJECTS, ReleaseResult, detect_changes, release_project

app = FastAPI(
    title="CK Develop Release API",
    description="Monorepo 子项目独立发布接口",
    version="1.0.0",
)


def _handle_release(project_key: str, force: bool) -> dict:
    try:
        result: ReleaseResult = release_project(project_key, force=force)
        return result.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/release/project-a/check")
def check_project_a() -> dict:
    """检查 project-a 在本次 push 中是否有变更。"""
    changed, files = detect_changes(PROJECTS["project-a"]["dir"])
    return {"project": "project-a", "changed": changed, "changed_files": files}


@app.get("/release/project-b/check")
def check_project_b() -> dict:
    """检查 project-b 在本次 push 中是否有变更。"""
    changed, files = detect_changes(PROJECTS["project-b"]["dir"])
    return {"project": "project-b", "changed": changed, "changed_files": files}


@app.post("/release/project-a")
def release_project_a(
    force: bool = Query(False, description="强制发布，忽略变更检测"),
) -> dict:
    """
    发布 project-a：
    - 检测 project-a/ 目录变更
    - 递增版本并打 tag（a-v1.0.0 格式）
    """
    return _handle_release("project-a", force)


@app.post("/release/project-b")
def release_project_b(
    force: bool = Query(False, description="强制发布，忽略变更检测"),
) -> dict:
    """
    发布 project-b：
    - 检测 project-b/ 目录变更
    - 递增版本并打 tag（b-v1.0.0 格式）
    """
    return _handle_release("project-b", force)
