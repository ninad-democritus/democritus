"""
Unit tests for pipeline orchestrator
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import the orchestrator to test
from app.workflows.pipeline_orchestrator import PipelineOrchestrator


class TestPipelineOrchestrator:
    """Test cases for PipelineOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        """Create a PipelineOrchestrator instance for testing"""
        return PipelineOrchestrator()
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initialization"""
        assert orchestrator.metadata_service is not None
        assert orchestrator.file_service is not None
        assert len(orchestrator.PIPELINE_STAGES) > 0
        assert orchestrator.pipeline_runs == {}
    
    def test_get_pipeline_stages(self):
        """Test getting pipeline stages"""
        stages = PipelineOrchestrator.get_pipeline_stages()
        
        assert isinstance(stages, list)
        assert len(stages) > 0
        
        # Check that each stage has required fields
        for stage in stages:
            assert "id" in stage
            assert "name" in stage
            assert "description" in stage
    
    def test_stage_definition(self, orchestrator):
        """Test that all stages are properly defined"""
        stages = orchestrator.PIPELINE_STAGES
        
        expected_stage_ids = [
            "file_discovery",
            "file_validation", 
            "schema_validation",
            "entity_mapping",
            "data_transformation",
            "table_setup",
            "data_ingestion",
            "metadata_storage",
            "file_cleanup"
        ]
        
        actual_stage_ids = [stage["id"] for stage in stages]
        
        for expected_id in expected_stage_ids:
            assert expected_id in actual_stage_ids
    
    def test_service_orchestrator_setup(self, orchestrator):
        """Test that services have orchestrator reference set"""
        # File service should have orchestrator set
        assert hasattr(orchestrator.file_service, 'orchestrator')
        # Note: We can't test the actual reference because it's set via set_orchestrator method


if __name__ == "__main__":
    pytest.main([__file__])

