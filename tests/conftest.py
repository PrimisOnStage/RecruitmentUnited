from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_llama_cloud_stub() -> None:
    module = types.ModuleType("llama_cloud")

    class _DummyExtractionAgents:
        def list(self):
            return []

        def create(self, name, data_schema, config):
            return types.SimpleNamespace(id="agent-1", name=name, data_schema=data_schema, config=config)

    class _DummyJobs:
        def extract(self, extraction_agent_id, file_id):
            return types.SimpleNamespace(data={})

    class _DummyFiles:
        def create(self, file, purpose):
            return types.SimpleNamespace(id="file-1", file=file, purpose=purpose)

    class LlamaCloud:
        def __init__(self):
            self.extraction = types.SimpleNamespace(
                extraction_agents=_DummyExtractionAgents(),
                jobs=_DummyJobs(),
            )
            self.files = _DummyFiles()

    module.LlamaCloud = LlamaCloud
    sys.modules["llama_cloud"] = module


def _install_google_stubs() -> None:
    google_module = sys.modules.setdefault("google", types.ModuleType("google"))
    auth_module = sys.modules.setdefault("google.auth", types.ModuleType("google.auth"))
    transport_module = sys.modules.setdefault("google.auth.transport", types.ModuleType("google.auth.transport"))
    requests_module = types.ModuleType("google.auth.transport.requests")

    class Request:
        pass

    requests_module.Request = Request
    sys.modules["google.auth.transport.requests"] = requests_module
    auth_module.transport = transport_module
    transport_module.requests = requests_module
    google_module.auth = auth_module

    oauth2_module = sys.modules.setdefault("google.oauth2", types.ModuleType("google.oauth2"))
    credentials_module = types.ModuleType("google.oauth2.credentials")

    class Credentials:
        def __init__(self, valid=True, expired=False, refresh_token=None):
            self.valid = valid
            self.expired = expired
            self.refresh_token = refresh_token

        @classmethod
        def from_authorized_user_file(cls, *_args, **_kwargs):
            return cls(valid=True)

        def refresh(self, _request):
            self.valid = True

        def to_json(self):
            return "{}"

    credentials_module.Credentials = Credentials
    sys.modules["google.oauth2.credentials"] = credentials_module
    oauth2_module.credentials = credentials_module
    google_module.oauth2 = oauth2_module

    oauthlib_module = types.ModuleType("google_auth_oauthlib")
    flow_module = types.ModuleType("google_auth_oauthlib.flow")

    class InstalledAppFlow:
        @classmethod
        def from_client_secrets_file(cls, *_args, **_kwargs):
            return cls()

        def run_local_server(self, port=0):
            return Credentials(valid=True)

    flow_module.InstalledAppFlow = InstalledAppFlow
    oauthlib_module.flow = flow_module
    sys.modules["google_auth_oauthlib"] = oauthlib_module
    sys.modules["google_auth_oauthlib.flow"] = flow_module

    googleapiclient_module = types.ModuleType("googleapiclient")
    discovery_module = types.ModuleType("googleapiclient.discovery")

    def build(*_args, **_kwargs):
        return types.SimpleNamespace()

    discovery_module.build = build
    googleapiclient_module.discovery = discovery_module
    sys.modules["googleapiclient"] = googleapiclient_module
    sys.modules["googleapiclient.discovery"] = discovery_module


def _install_vector_store_stub() -> None:
    module = types.ModuleType("backend.processing.vector_store")
    module.index_candidate = lambda *args, **kwargs: None
    module.search_candidates = lambda *args, **kwargs: []
    module.index_all_existing_candidates = lambda conn: None
    sys.modules["backend.processing.vector_store"] = module


_install_llama_cloud_stub()
_install_google_stubs()
_install_vector_store_stub()
main = importlib.import_module("backend.main")
candidates_routes = importlib.import_module("backend.api.routes.candidates")
candidate_repository = importlib.import_module("backend.services.candidate_repository")


@pytest.fixture
def main_module(monkeypatch):
    monkeypatch.setattr(main, "init_db", lambda: None)
    return main


@pytest.fixture
def candidates_routes_module():
    return candidates_routes


@pytest.fixture
def candidate_repository_module():
    return candidate_repository


@pytest.fixture
def client(main_module):
    with TestClient(main_module.app) as test_client:
        yield test_client

