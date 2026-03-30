import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from src.infrastructure.storage import S3Storage
from src.application.services import DataSyncService
from src.domain.interfaces import IDataStorage


class TestS3Storage:
    @pytest.fixture
    def mock_boto3(self):
        with patch('src.infrastructure.storage.boto3') as mock:
            yield mock

    @pytest.fixture
    def s3_config(self):
        return {
            "endpoint_url": "http://localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "bucket": "datasets"
        }

    def test_s3_storage_initialization(self, mock_boto3, s3_config):
        storage = S3Storage(**s3_config)
        
        mock_boto3.client.assert_called_once_with(
            's3',
            endpoint_url=s3_config["endpoint_url"],
            aws_access_key_id=s3_config["access_key"],
            aws_secret_access_key=s3_config["secret_key"]
        )
        assert storage.bucket == s3_config["bucket"]

    def test_s3_download_file(self, mock_boto3, s3_config):
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
        mock_client = MagicMock()
        mock_client.download_file.side_effect = Exception("Connection failed")
        mock_boto3.client.return_value = mock_client
        
        storage = S3Storage(**s3_config)
        
        with pytest.raises(Exception) as exc_info:
            storage.download_file("remote/file.csv", "local/file.csv")
        
        assert "Connection failed" in str(exc_info.value)

    def test_s3_upload_file_error_handling(self, mock_boto3, s3_config):
        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception("Write permission denied")
        mock_boto3.client.return_value = mock_client
        
        storage = S3Storage(**s3_config)
        
        with pytest.raises(Exception) as exc_info:
            storage.upload_file("local/file.csv", "remote/file.csv")
        
        assert "Write permission denied" in str(exc_info.value)


class TestDataSyncService:
    @pytest.fixture
    def mock_storage(self):
        storage = MagicMock()
        storage.download_file = MagicMock()
        return storage

    def test_sync_downloads_when_file_not_exists(self, mock_storage):
        with patch('src.application.services.Path') as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            MockPath.return_value = mock_path_instance
            
            service = DataSyncService(storage=mock_storage)
            service.sync_dataset("remote/data.csv", "data/data.csv")
            
            mock_storage.download_file.assert_called_once_with("remote/data.csv", "data/data.csv")

    def test_sync_skips_download_when_file_exists(self, mock_storage):
        with patch('src.application.services.Path') as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            MockPath.return_value = mock_path_instance
            
            service = DataSyncService(storage=mock_storage)
            service.sync_dataset("remote/data.csv", "local/data.csv")
            mock_storage.download_file.assert_not_called()

    def test_sync_downloads_when_file_exists_with_force(self, mock_storage):
        with patch('src.application.services.Path') as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            MockPath.return_value = mock_path_instance
            
            service = DataSyncService(storage=mock_storage)
            service.sync_dataset("remote/data.csv", "local/data.csv", force=True)
            mock_storage.download_file.assert_called_once_with("remote/data.csv", "local/data.csv")

    def test_sync_creates_directory_if_needed(self, mock_storage):
        with patch('src.application.services.Path') as MockPath:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_instance.parent = MagicMock()
            MockPath.return_value = mock_path_instance
            
            service = DataSyncService(storage=mock_storage)
            service.sync_dataset("remote/data.csv", "local/nested/data.csv")
            
            mock_path_instance.parent.mkdir.assert_called_with(parents=True, exist_ok=True)



class TestS3StorageIntegration:
    @pytest.fixture
    def mock_boto3_with_behavior(self):
        with patch('src.infrastructure.storage.boto3') as mock:
            mock_client = MagicMock()
            mock.client.return_value = mock_client
            yield mock, mock_client

    def test_full_download_workflow(self, mock_boto3_with_behavior, tmp_path):
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
