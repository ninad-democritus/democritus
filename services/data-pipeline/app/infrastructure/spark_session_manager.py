"""
Spark Session Manager for centralized Spark session management
"""

import logging
import os
from typing import Optional
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf

logger = logging.getLogger(__name__)


class SparkSessionManager:
    """Singleton manager for Spark sessions with optimized configuration"""
    
    _instance: Optional['SparkSessionManager'] = None
    _spark_session: Optional[SparkSession] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SparkSessionManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the Spark session manager"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            logger.info("Initializing SparkSessionManager")
    
    @classmethod
    def get_session(cls) -> SparkSession:
        """Get or create the Spark session"""
        instance = cls()
        if instance._spark_session is None:
            instance._spark_session = instance._create_session()
        return instance._spark_session
    
    def _create_session(self) -> SparkSession:
        """Create a new Spark session with optimized configuration"""
        logger.info("Creating new Spark session with Iceberg and S3 support")
        
        # Iceberg packages for Spark 3.5.0
        iceberg_packages = [
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.2",
            "org.apache.hadoop:hadoop-aws:3.3.4",
            "com.amazonaws:aws-java-sdk-bundle:1.12.470"
        ]
        
        # Create Spark configuration
        conf = SparkConf()
        
        # Basic Spark configuration
        conf.set("spark.app.name", "DataPipelineIcebergService")
        conf.set("spark.master", "local[*]")
        conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        
        # Iceberg configuration
        conf.set("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        conf.set("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog")
        conf.set("spark.sql.catalog.spark_catalog.type", "hive")
        conf.set("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog")
        conf.set("spark.sql.catalog.iceberg_catalog.type", "rest")
        conf.set("spark.sql.catalog.iceberg_catalog.uri", "http://iceberg-rest:8181")
        
        # S3 configuration for MinIO
        conf.set("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
        conf.set("spark.hadoop.fs.s3a.access.key", "minioadmin")
        conf.set("spark.hadoop.fs.s3a.secret.key", "minioadmin")
        conf.set("spark.hadoop.fs.s3a.path.style.access", "true")
        conf.set("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        conf.set("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        
        # AWS region configuration
        conf.set("spark.hadoop.fs.s3a.aws.credentials.provider", 
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        
        # Environment variables for AWS SDK
        os.environ["AWS_REGION"] = "us-east-1"
        os.environ["AWS_ACCESS_KEY_ID"] = "minioadmin"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "minioadmin"
        
        # Performance optimizations
        conf.set("spark.sql.adaptive.enabled", "true")
        conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
        conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
        
        # Memory configuration
        conf.set("spark.driver.memory", "2g")
        conf.set("spark.executor.memory", "2g")
        conf.set("spark.driver.maxResultSize", "1g")
        
        # Create Spark session
        spark = (SparkSession.builder
                .config(conf=conf)
                .config("spark.jars.packages", ",".join(iceberg_packages))
                .getOrCreate())
        
        # Set log level to reduce noise
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info("Spark session created successfully")
        return spark
    
    @classmethod
    def stop_session(cls) -> None:
        """Stop the current Spark session"""
        instance = cls()
        if instance._spark_session is not None:
            logger.info("Stopping Spark session")
            instance._spark_session.stop()
            instance._spark_session = None
    
    @classmethod
    def restart_session(cls) -> SparkSession:
        """Restart the Spark session"""
        cls.stop_session()
        return cls.get_session()
    
    def is_session_active(self) -> bool:
        """Check if Spark session is active"""
        return (self._spark_session is not None and 
                not self._spark_session.sparkContext._jsc.sc().isStopped())
    
    def get_session_info(self) -> dict:
        """Get information about the current Spark session"""
        if self._spark_session is None:
            return {"status": "not_initialized"}
        
        return {
            "status": "active" if self.is_session_active() else "stopped",
            "app_name": self._spark_session.sparkContext.appName,
            "app_id": self._spark_session.sparkContext.applicationId,
            "master": self._spark_session.sparkContext.master,
            "version": self._spark_session.version
        }
    
    def __del__(self):
        """Cleanup when manager is destroyed"""
        if hasattr(self, '_spark_session') and self._spark_session is not None:
            try:
                self._spark_session.stop()
            except Exception as e:
                logger.warning(f"Error stopping Spark session during cleanup: {e}")

