import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.routes import projects, files


@pytest.fixture(autouse=True)
def tmp_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_STORAGE_PATH", str(tmp_path))
    # Patch the module-level objects
    from app.storage import ProjectIndex
    new_index = ProjectIndex(tmp_path)
    projects.index = new_index
    projects.STORAGE_PATH = tmp_path
    files.index = new_index
    files.STORAGE_PATH = tmp_path
    yield tmp_path


@pytest.fixture
def client():
    return TestClient(app)


# --- Project CRUD ---

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_project(client):
    res = client.post("/projects", json={"name": "Test Project"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Test Project"
    assert len(data["id"]) == 12
    assert data["status"] == "active"


def test_create_project_default_name(client):
    res = client.post("/projects")
    assert res.status_code == 201
    assert res.json()["name"] == "Untitled Presentation"


def test_list_projects(client):
    client.post("/projects", json={"name": "Project A"})
    client.post("/projects", json={"name": "Project B"})
    res = client.get("/projects")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2


def test_get_project(client):
    created = client.post("/projects", json={"name": "My Project"}).json()
    res = client.get(f"/projects/{created['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "My Project"
    assert "files" in data
    assert "artifacts" in data
    assert data["message_count"] == 1  # initial greeting message


def test_rename_project(client):
    created = client.post("/projects").json()
    res = client.patch(f"/projects/{created['id']}", json={"name": "Renamed"})
    assert res.status_code == 200
    assert res.json()["name"] == "Renamed"


def test_delete_project(client):
    created = client.post("/projects").json()
    res = client.delete(f"/projects/{created['id']}")
    assert res.status_code == 204
    # Verify it's gone
    res = client.get(f"/projects/{created['id']}")
    assert res.status_code == 404


def test_project_not_found(client):
    res = client.get("/projects/nonexistent")
    assert res.status_code == 404


# --- File management ---

def test_upload_files(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    res = client.post(
        f"/projects/{pid}/files",
        files=[("files", ("data.csv", b"a,b,c\n1,2,3", "text/csv"))],
    )
    assert res.status_code == 201
    data = res.json()
    assert len(data) == 1
    assert data[0]["filename"] == "data.csv"


def test_list_files(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    client.post(
        f"/projects/{pid}/files",
        files=[("files", ("data.csv", b"a,b,c", "text/csv"))],
    )
    res = client.get(f"/projects/{pid}/files")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_rename_file(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    client.post(
        f"/projects/{pid}/files",
        files=[("files", ("old.csv", b"a,b,c", "text/csv"))],
    )
    res = client.patch(f"/projects/{pid}/files/old.csv", json={"name": "new.csv"})
    assert res.status_code == 200
    assert res.json()["filename"] == "new.csv"


def test_add_note_to_file(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    client.post(
        f"/projects/{pid}/files",
        files=[("files", ("data.csv", b"a,b,c", "text/csv"))],
    )
    res = client.patch(
        f"/projects/{pid}/files/data.csv",
        json={"note": "This is revenue data"},
    )
    assert res.status_code == 200
    assert res.json()["note"] == "This is revenue data"


def test_delete_file(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    client.post(
        f"/projects/{pid}/files",
        files=[("files", ("data.csv", b"a,b,c", "text/csv"))],
    )
    res = client.delete(f"/projects/{pid}/files/data.csv")
    assert res.status_code == 204

    files_list = client.get(f"/projects/{pid}/files").json()
    assert len(files_list) == 0


def test_download_file(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    client.post(
        f"/projects/{pid}/files",
        files=[("files", ("data.csv", b"a,b,c\n1,2,3", "text/csv"))],
    )
    res = client.get(f"/projects/{pid}/files/data.csv/download")
    assert res.status_code == 200
    assert res.content == b"a,b,c\n1,2,3"


def test_file_not_found(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    res = client.delete(f"/projects/{pid}/files/nonexistent.csv")
    assert res.status_code == 404


def test_artifact_not_found(client):
    proj = client.post("/projects").json()
    pid = proj["id"]

    res = client.get(f"/projects/{pid}/artifacts/nonexistent.pdf")
    assert res.status_code == 404
