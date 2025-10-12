"""
Core API Module for Query Service

This module provides stable, versioned REST endpoints for external services
(like Dashboard Service) to access core query functionality without depending
on the internal LangGraph workflow implementation.

Endpoints:
- /core/v1/validate-sql: Validate SQL queries
- /core/v1/execute-sql: Execute SQL queries
- /core/v1/bind-chart-data: Bind data to chart configurations
"""

from .routes import router

__all__ = ["router"]

