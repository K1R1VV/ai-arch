"""
Unit tests for S3Storage and DataSyncService with mocked boto3 client.
Tests focus on synchronization logic without requiring real MinIO connection.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from src.infrastructure.storage import S3Storage
from src.application.services import DataSyncService
from src.domain.interfaces import IDataStorage


class TestS3Storage:
    """Tests for S3Storage class with mocked boto3 client"""

    @pytest.fixture
    def mock_boto3(self):
        """Mock boto3 client"""
        with patch('src.infrastructure.storage.boto3') as mock:
            yield mock

    @pytest.fixture
    def s3_config(self):
        """Standard S3 configuration"""
        return {
            "endpoint_url": "http://localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "bucket": "datasets"
        }

    def test_s3_storage_initialization(self, mock_boto3, s3_config):
        """Test S3Storage initializes with correct boto3 client"""
        storage = S3Storage(**s3_config)
        
        mock_boto3.client.assert_called_once_with(
            's3',
            endpoint_url=s3_config["endpoint_url"],
            aws_access_key_id=s3_config["access_key"],
            aws_secret_access_key=s3_config["secret_key"]
        )
        assert storage.bucket == s3_config["bucket"]

    def test_s3_download_file(self, mock_boto3, s3_config):
        """Test downloading a file from S3"""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        storage = S3Storage(**s3_config)
        storage.download_file("remote/path/file.csv", "local/file.csv")
        
        mock_client.download_file.assert_called_once_with(
            "datasets",
            "remote/path/file.csv",
            "local/file.csv"
        )

    def test_s3_upload_file(self, mock_boto3, s3_config):
        """Test uploading a file to S3"""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        storage = S3Storage(**s3_config)
        storage.upload_file("local/file.csv", "remote/path/file.csv")
        
        mock_client.upload_file.assert_called_once_with(
            "local/file.csv",
            "datasets",
            "remote/path/file.csv"
        )

    def test_s3_download_file_error_handling(self, mock_boto3, s3_config):
        """Test error handling when download fails"""
        mock_client = MagicMock()
        mock_client.download_file.side_effect = Exception("Connection failed")
        mock_boto3.client.return_value = mock_client
        
        storage = S3Storage(**s3_config)
        
        with pytest.raises(Exception) as exc_info:
            storage.download_file("remote/file.csv", "local/file.csv")
        
        assert "Connection failed" in str(exc_info.value)

    def test_s3_upload_file_error_handling(self, mock_boto3, s3_config):
        """Test error handling when upload fails"""
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception("Write permission denied")
        mock_boto3.client.return_value = mock_client
        
        storage = S3Storage(**s3_config)
        
        with pytest.raises(Exception) as exc_info:
            storage.upload_file("local/file.csv", "remote/file.csv")
        
        assert "Write permission denied" in str(exc_info.value)


class TestDataSyncService:
    """Tests for DataSyncService synchronization logic"""

    @pytest.fixture
    def mock_storage(self):
        """Mock storage interface"""
        storage = MagicMock(spec=IDataStorage)
        return storage

    def test_sync_downloads_when_file_missing(self, mock_storage, tmp_path):
        """Test sync downloads file when it doesn't exist locally"""
        local_path = tmp_path / "data" / "ratings.csv"
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset("data/ratings.csv", str(local_path))
        
        mock_storage.download_file.assert_called_once_with(
            "data/ratings.csv",
            str(local_path)
        )
        assert local_path.parent.exists()

    def test_sync_skips_download_when_file_exists(self, mock_storage, tmp_path):
        """Test sync skips download when file already exists"""
        local_path = tmp_path / "data" / "ratings.csv"
        local_path.parent.mkdir(parents=True)
        local_path.write_text("user_id,movie_id,rating\n1,101,5.0\n")
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset("data/ratings.csv", str(local_path))
        
        mock_storage.download_file.assert_not_called()

    def test_sync_creates_nested_directories(self, mock_storage, tmp_path):
        """Test sync creates all necessary parent directories"""
        local_path = tmp_path / "deep" / "nested" / "path" / "data" / "ratings.csv"
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset("data/ratings.csv", str(local_path))
        
        assert local_path.parent.exists()
        assert local_path.parent.is_dir()

    def test_sync_with_multiple_files_sequence(self, mock_storage, tmp_path):
        """Test sequential syncing of multiple files"""
        service = DataSyncService(storage=mock_storage)
        
        files = [
            ("data/ratings.csv", str(tmp_path / "ratings.csv")),
            ("data/models.pkl", str(tmp_path / "models.pkl")),
        ]
        
        for remote, local in files:
            service.sync_dataset(remote, local)
        
        assert mock_storage.download_file.call_count == 2
        calls = [
            call("data/ratings.csv", str(tmp_path / "ratings.csv")),
            call("data/models.pkl", str(tmp_path / "models.pkl")),
        ]
        mock_storage.download_file.assert_has_calls(calls)

    def test_sync_handles_storage_exception(self, mock_storage, tmp_path):
        """Test sync properly propagates storage exceptions"""
        mock_storage.download_file.side_effect = Exception("S3 connection timeout")
        local_path = tmp_path / "data" / "ratings.csv"
        
        service = DataSyncService(storage=mock_storage)
        
        with pytest.raises(Exception) as exc_info:
            service.sync_dataset("data/ratings.csv", str(local_path))
        
        assert "S3 connection timeout" in str(exc_info.value)

    def test_sync_file_with_special_characters_in_path(self, mock_storage, tmp_path):
        """Test sync works with special characters in paths"""
        local_path = tmp_path / "data-v2.0" / "ratings_2024-03-06.csv"
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset("data-v2.0/ratings_2024-03-06.csv", str(local_path))
        
        mock_storage.download_file.assert_called_once()
        assert local_path.parent.exists()

    def test_sync_preserves_file_path_structure(self, mock_storage, tmp_path):
        """Test sync maintains the exact path structure specified"""
        remote_path = "archives/2024/q1/ratings.csv"
        local_path = str(tmp_path / "cache" / "archives" / "2024" / "q1" / "ratings.csv")
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset(remote_path, local_path)
        
        mock_storage.download_file.assert_called_once_with(remote_path, local_path)


class TestS3StorageIntegration:
    """Integration-style tests with mocked boto3 (but testing real logic flow)"""

    @pytest.fixture
    def mock_boto3_with_behavior(self):
        """More realistic mock boto3 with call tracking"""
        with patch('src.infrastructure.storage.boto3') as mock:
            mock_client = MagicMock()
            mock.client.return_value = mock_client
            yield mock, mock_client

    def test_full_download_workflow(self, mock_boto3_with_behavior, tmp_path):
        """Test complete download workflow"""
        mock, mock_client = mock_boto3_with_behavior
        
        config = {
            "endpoint_url": "http://localhost:9000",
            "access_key": "test",
            "secret_key": "test",
            "bucket": "test-bucket"
        }
        
        storage = S3Storage(**config)
        local_file = tmp_path / "downloaded.csv"
        storage.download_file("source/file.csv", str(local_file))
        
        mock.client.assert_called_once()
        mock_client.download_file.assert_called_once_with(
            "test-bucket",
            "source/file.csv",
            str(local_file)
        )

    def test_storage_retains_configuration(self, mock_boto3_with_behavior):
        """Test storage retains configuration after initialization"""
        mock, _ = mock_boto3_with_behavior
        
        config = {
            "endpoint_url": "http://minio.example.com:9000",
            "access_key": "custom_key",
            "secret_key": "custom_secret",
            "bucket": "custom-bucket"
        }
        
        storage = S3Storage(**config)
        
        assert storage.bucket == "custom-bucket"
        mock.client.assert_called_once_with(
            's3',
            endpoint_url="http://minio.example.com:9000",
            aws_access_key_id="custom_key",
            aws_secret_access_key="custom_secret"
        )
