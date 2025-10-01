"""
Unit tests for infrastructure services
"""

import pytest
import unittest.mock as mock
from unittest.mock import Mock, patch, MagicMock
import os
from datetime import datetime

from app.infrastructure.spark_session_manager import SparkSessionManager
from app.infrastructure.minio_client_manager import MinioClientManager


class TestSparkSessionManager:
    """Test cases for SparkSessionManager"""
    
    def setup_method(self):
        """Reset singleton instance before each test"""
        SparkSessionManager._instance = None
        SparkSessionManager._spark_session = None
    
    def test_singleton_pattern(self):
        """Test that SparkSessionManager follows singleton pattern"""
        manager1 = SparkSessionManager()
        manager2 = SparkSessionManager()
        assert manager1 is manager2
    
    @patch('app.infrastructure.spark_session_manager.SparkSession')
    def test_get_session_creates_session(self, mock_spark_session):
        """Test that get_session creates a Spark session"""
        mock_session = Mock()
        mock_builder = Mock()
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_session
        mock_spark_session.builder = mock_builder
        
        session = SparkSessionManager.get_session()
        
        assert session is mock_session
        mock_builder.getOrCreate.assert_called_once()
    
    @patch('app.infrastructure.spark_session_manager.SparkSession')
    def test_get_session_reuses_existing_session(self, mock_spark_session):
        """Test that get_session reuses existing session"""
        mock_session = Mock()
        mock_builder = Mock()
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_session
        mock_spark_session.builder = mock_builder
        
        session1 = SparkSessionManager.get_session()
        session2 = SparkSessionManager.get_session()
        
        assert session1 is session2
        mock_builder.getOrCreate.assert_called_once()
    
    @patch('app.infrastructure.spark_session_manager.SparkSession')
    def test_stop_session(self, mock_spark_session):
        """Test stopping Spark session"""
        mock_session = Mock()
        mock_builder = Mock()
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_session
        mock_spark_session.builder = mock_builder
        
        # Create session first
        SparkSessionManager.get_session()
        
        # Stop session
        SparkSessionManager.stop_session()
        
        mock_session.stop.assert_called_once()
    
    @patch('app.infrastructure.spark_session_manager.SparkSession')
    def test_restart_session(self, mock_spark_session):
        """Test restarting Spark session"""
        mock_session = Mock()
        mock_builder = Mock()
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_session
        mock_spark_session.builder = mock_builder
        
        # Create and restart session
        SparkSessionManager.get_session()
        new_session = SparkSessionManager.restart_session()
        
        assert new_session is mock_session
        mock_session.stop.assert_called_once()
    
    @patch('app.infrastructure.spark_session_manager.SparkSession')
    def test_is_session_active(self, mock_spark_session):
        """Test checking if session is active"""
        mock_session = Mock()
        mock_session.sparkContext._jsc.sc.return_value.isStopped.return_value = False
        mock_builder = Mock()
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_session
        mock_spark_session.builder = mock_builder
        
        manager = SparkSessionManager()
        
        # No session initially
        assert not manager.is_session_active()
        
        # Create session
        SparkSessionManager.get_session()
        assert manager.is_session_active()
    
    @patch('app.infrastructure.spark_session_manager.SparkSession')
    def test_get_session_info(self, mock_spark_session):
        """Test getting session information"""
        mock_session = Mock()
        mock_session.sparkContext.appName = "TestApp"
        mock_session.sparkContext.applicationId = "app-123"
        mock_session.sparkContext.master = "local[*]"
        mock_session.version = "3.5.0"
        mock_session.sparkContext._jsc.sc.return_value.isStopped.return_value = False
        
        mock_builder = Mock()
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = mock_session
        mock_spark_session.builder = mock_builder
        
        manager = SparkSessionManager()
        
        # No session initially
        info = manager.get_session_info()
        assert info["status"] == "not_initialized"
        
        # Create session
        SparkSessionManager.get_session()
        info = manager.get_session_info()
        
        assert info["status"] == "active"
        assert info["app_name"] == "TestApp"
        assert info["app_id"] == "app-123"
        assert info["master"] == "local[*]"
        assert info["version"] == "3.5.0"


class TestMinioClientManager:
    """Test cases for MinioClientManager"""
    
    def setup_method(self):
        """Reset singleton instance before each test"""
        MinioClientManager._instance = None
        MinioClientManager._client = None
    
    def test_singleton_pattern(self):
        """Test that MinioClientManager follows singleton pattern"""
        manager1 = MinioClientManager()
        manager2 = MinioClientManager()
        assert manager1 is manager2
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_get_client_creates_client(self, mock_minio):
        """Test that get_client creates a MinIO client"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        
        # Mock successful connection test
        mock_client.list_buckets.return_value = []
        
        client = MinioClientManager.get_client()
        
        assert client is mock_client
        mock_minio.assert_called_once()
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_get_client_reuses_existing_client(self, mock_minio):
        """Test that get_client reuses existing client"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        
        client1 = MinioClientManager.get_client()
        client2 = MinioClientManager.get_client()
        
        assert client1 is client2
        mock_minio.assert_called_once()
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_ensure_bucket_exists_creates_bucket(self, mock_minio):
        """Test creating bucket if it doesn't exist"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        mock_client.bucket_exists.return_value = False
        
        result = MinioClientManager.ensure_bucket_exists("test-bucket")
        
        assert result is True
        mock_client.make_bucket.assert_called_once_with("test-bucket")
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_ensure_bucket_exists_bucket_already_exists(self, mock_minio):
        """Test when bucket already exists"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        mock_client.bucket_exists.return_value = True
        
        result = MinioClientManager.ensure_bucket_exists("test-bucket")
        
        assert result is True
        mock_client.make_bucket.assert_not_called()
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_list_objects(self, mock_minio):
        """Test listing objects in bucket"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        
        # Mock object
        mock_obj = Mock()
        mock_obj.object_name = "test.csv"
        mock_obj.size = 1024
        mock_obj.etag = "abc123"
        mock_obj.last_modified = datetime.now()
        mock_obj.content_type = "text/csv"
        
        mock_client.list_objects.return_value = [mock_obj]
        
        objects = MinioClientManager.list_objects("test-bucket", "prefix/")
        
        assert len(objects) == 1
        assert objects[0]["object_name"] == "test.csv"
        assert objects[0]["size"] == 1024
        mock_client.list_objects.assert_called_once_with("test-bucket", prefix="prefix/", recursive=True)
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_object_exists(self, mock_minio):
        """Test checking if object exists"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        
        # Object exists
        mock_client.stat_object.return_value = Mock()
        result = MinioClientManager.object_exists("bucket", "object")
        assert result is True
        
        # Object doesn't exist
        from minio.error import S3Error
        mock_client.stat_object.side_effect = S3Error("NoSuchKey", "Object not found", "resource", "request_id", "host_id", "response")
        result = MinioClientManager.object_exists("bucket", "object")
        assert result is False
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_delete_object(self, mock_minio):
        """Test deleting an object"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        
        result = MinioClientManager.delete_object("bucket", "object")
        
        assert result is True
        mock_client.remove_object.assert_called_once_with("bucket", "object")
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_get_presigned_url(self, mock_minio):
        """Test generating presigned URL"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        mock_client.presigned_get_object.return_value = "https://presigned-url"
        
        url = MinioClientManager.get_presigned_url("bucket", "object")
        
        assert url == "https://presigned-url"
        mock_client.presigned_get_object.assert_called_once()
    
    def test_get_client_info(self):
        """Test getting client information"""
        manager = MinioClientManager()
        info = manager.get_client_info()
        
        assert "endpoint" in info
        assert "secure" in info
        assert "connected" in info
        assert info["endpoint"] == "minio:9000"
        assert info["secure"] is False
    
    @patch('app.infrastructure.minio_client_manager.Minio')
    def test_reset_client(self, mock_minio):
        """Test resetting client"""
        mock_client = Mock()
        mock_minio.return_value = mock_client
        mock_client.list_buckets.return_value = []
        
        # Create client first
        MinioClientManager.get_client()
        
        # Reset client
        MinioClientManager.reset_client()
        
        # Get client again should create new one
        new_client = MinioClientManager.get_client()
        assert mock_minio.call_count == 2

