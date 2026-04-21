import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_thumbnail_service():
    with patch('app.routers.thumbnail.get_thumbnail_service') as mock:
        service = Mock()
        service.generate = AsyncMock(return_value="/tmp/output.png")
        service.generate_from_bytes = AsyncMock(b"image_data")
        mock.return_value = service
        yield service


@pytest.fixture
def mock_s3_service():
    with patch('app.routers.thumbnail.get_s3_service') as mock:
        service = Mock()
        service.download_file = AsyncMock()
        service.upload_file = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "supported_formats" in data


def test_thumbnail_options_validation():
    from app.models.schemas import ThumbnailOptionsRequest
    
    options = ThumbnailOptionsRequest(
        width=300,
        height=300,
        quality=85,
        trim=False,
        type="thumbnail",
        output_format="png"
    )
    
    assert options.width == 300
    assert options.height == 300
    assert options.quality == 85
    assert options.output_format == "png"


def test_thumbnail_options_defaults():
    from app.models.schemas import ThumbnailOptionsRequest
    
    options = ThumbnailOptionsRequest()
    
    assert options.width == 300
    assert options.height == 300
    assert options.quality == 85
    assert options.type == "thumbnail"
    assert options.output_format == "png"


def test_s3_input_request():
    from app.models.schemas import S3InputRequest
    
    request = S3InputRequest(
        s3_path="bucket/file.pdf",
        options=ThumbnailOptionsRequest()
    )
    
    assert request.s3_path == "bucket/file.pdf"


def test_local_file_request():
    from app.models.schemas import LocalFileRequest
    
    request = LocalFileRequest(
        file_path="/path/to/file.pdf",
        output_path="/path/to/output.png",
        options=ThumbnailOptionsRequest()
    )
    
    assert request.file_path == "/path/to/file.pdf"
    assert request.output_path == "/path/to/output.png"
