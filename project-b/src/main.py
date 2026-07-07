"""Project B - Web API"""

from pathlib import Path

from fastapi import FastAPI

VERSION = Path(__file__).resolve().parent.parent.joinpath("VERSION").read_text().strip()

app = FastAPI(title="Project B", version=VERSION)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": f"Hello from Project B v{VERSION}"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "project": "project-b", "version": VERSION}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9090)
