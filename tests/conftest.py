import pytest
@pytest.fixture
def mock_document():
    return {"id": "doc_123", "name": "sample.pdf"}
