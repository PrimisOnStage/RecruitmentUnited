class RecordingCursor:
    def __init__(self, *, fetchall_result=None, fetchone_result=None):
        self.fetchall_result = fetchall_result or []
        self.fetchone_result = fetchone_result
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.fetchall_result

    def fetchone(self):
        return self.fetchone_result

    def close(self):
        return None


class RecordingConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_get_candidates_applies_min_exp_even_when_zero(client, candidate_repository_module, monkeypatch):
    cursor = RecordingCursor(
        fetchall_result=[
            (1, "Ada Lovelace", "ada@example.com", "UK", "London", "Engineer", 0, ["python"], "applied", "linkedin")
        ]
    )
    connection = RecordingConnection(cursor)
    monkeypatch.setattr(candidate_repository_module, "get_connection", lambda: connection)

    response = client.get("/candidates", params={"min_exp": 0})

    assert response.status_code == 200
    assert response.json()[0]["exp"] == 0
    assert "experience_years >= %s" in cursor.executed[0][0]
    assert cursor.executed[0][1] == [0]


def test_get_candidates_rejects_negative_min_exp(client, candidate_repository_module, monkeypatch):
    monkeypatch.setattr(
        candidate_repository_module,
        "get_connection",
        lambda: (_ for _ in ()).throw(AssertionError("validation should fail before DB access")),
    )

    response = client.get("/candidates", params={"min_exp": -1})

    assert response.status_code == 422


def test_update_stage_rejects_invalid_stage_before_loading_candidate(client, candidates_routes_module, monkeypatch):
    monkeypatch.setattr(
        candidates_routes_module,
        "get_candidate_by_id",
        lambda _candidate_id: (_ for _ in ()).throw(AssertionError("invalid stage should fail before lookup")),
    )

    response = client.patch("/candidates/1/stage", params={"stage": "unknown"})

    assert response.status_code == 422


def test_update_stage_to_hired_syncs_hrms_and_persists_normalized_stage(client, candidates_routes_module, monkeypatch):
    push_calls = []
    cursor = RecordingCursor()

    monkeypatch.setattr(
        candidates_routes_module,
        "get_candidate_by_id",
        lambda candidate_id: {
            "id": candidate_id,
            "email": "ada@example.com",
            "source": "linkedin",
            "stage": "screening",
            "current_role": "Engineer",
        },
    )

    async def fake_push(candidate):
        push_calls.append(candidate)
        return {"status": "created"}

    monkeypatch.setattr(candidates_routes_module, "push_candidate_to_hrms", fake_push)
    monkeypatch.setattr(candidates_routes_module, "update_candidate_stage", lambda _id, _stage: cursor.execute("UPDATE", (_stage, _id)))

    response = client.patch("/candidates/7/stage", params={"stage": "hired"})

    assert response.status_code == 200
    assert response.json() == {"status": "updated"}
    assert len(push_calls) == 1
    assert cursor.executed[0][1] == ("hired", 7)


def test_update_stage_returns_not_found_for_missing_candidate(client, candidates_routes_module, monkeypatch):
    monkeypatch.setattr(candidates_routes_module, "get_candidate_by_id", lambda _candidate_id: None)

    response = client.patch("/candidates/99/stage", params={"stage": "applied"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Candidate not found"

