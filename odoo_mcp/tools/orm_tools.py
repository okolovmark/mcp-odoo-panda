"""
Odoo ORM Tools for MCP Server.
This module provides the main integration point for all ORM-related functionality
including schema introspection, domain validation, CRUD operations, and actions.
"""

import logging
from typing import Any, Dict, List, Optional

from odoo_mcp.tools.schema import SchemaIntrospector

logger = logging.getLogger(__name__)


class ORMTools:
    """Main ORM tools integration class for MCP server."""

    def __init__(self, connection_pool, config: Dict[str, Any]):
        """
        Initialize ORM tools.
        
        Args:
            connection_pool: Odoo connection pool
            config: Server configuration
        """
        self.pool = connection_pool
        self.config = config
        self.schema_introspector = SchemaIntrospector(connection_pool, config)

    async def _get_global_uid(self) -> int:
        """
        Get the global UID from the connection pool.
        
        Returns:
            int: Global UID for authentication
        """
        async with self.pool.get_connection() as connection:
            if hasattr(connection, 'global_uid'):
                # XMLRPC handler
                return connection.global_uid
            elif hasattr(connection, 'uid'):
                # JSONRPC handler
                return connection.uid
            else:
                raise Exception("No global UID found in connection")

    async def schema_version(self) -> Dict[str, str]:
        """
        Get schema version using global authentication.
        
        Returns:
            Dict with version information
        """
        global_uid = await self._get_global_uid()
        version_info = await self.schema_introspector.get_schema_version(global_uid)
        return {"version": version_info.version}

    async def schema_models(self, with_access: bool = True) -> Dict[str, List[str]]:
        """
        Get accessible models using global authentication.
        
        Args:
            with_access: Whether to filter by access rights
            
        Returns:
            Dict with list of accessible models
        """
        global_uid = await self._get_global_uid()
        models = await self.schema_introspector.list_models(global_uid, with_access=with_access)
        return {"models": models}

    async def schema_fields(self, model: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get fields for a specific model using global authentication.
        
        Args:
            model: Model name
            
        Returns:
            Dict with field information
        """
        global_uid = await self._get_global_uid()
        fields = await self.schema_introspector.list_fields(global_uid, model)
        # Convert to list format for response
        fields_list = []
        for field_name, field_info in fields.items():
            fields_list.append({
                "name": field_info.name,
                "ttype": field_info.ttype,
                "required": field_info.required,
                "readonly": field_info.readonly,
                "relation": field_info.relation,
                "selection": field_info.selection,
                "domain": field_info.domain,
                "store": field_info.store,
                "compute": field_info.compute,
                "writeable": field_info.writeable
            })
        return {"fields": fields_list}

    async def search_read(
        self,
        model: str,
        domain_json: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        order: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search and read records with security enhancements.
        
        Args:
            model: Model name
            domain_json: Search domain in JSON format
            fields: Fields to retrieve
            limit: Maximum number of records
            offset: Number of records to skip
            order: Order specification
            
        Returns:
            Dict with search results
        """
        result = await self.pool.execute_kw(
            model=model,
            method="search_read",
            args=[domain_json or []],
            kwargs={
                "fields": fields or ["id", "name"],
                "limit": limit,
                "offset": offset,
                "order": order
            }
        )
        return {
            "records": result,
            "count": len(result),
            "domain": compiled_domain
        }

    async def name_search(
        self,
        model: str,
        name: str,
        operator: str = "ilike",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search records by name with security.
        
        Args:
            model: Model name
            name: Name to search for
            operator: Search operator
            limit: Maximum number of results
            
        Returns:
            Dict with search results
        """
        result = await self.pool.execute_kw(
            model=model,
            method="name_search",
            args=[name],
            kwargs={"operator": operator, "limit": limit}
        )
        return {
            "results": result,
            "count": len(result)
        }

    async def read(
        self,
        model: str,
        record_ids: List[int],
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Read records with security.
        
        Args:
            model: Model name
            record_ids: List of record IDs
            fields: Fields to retrieve
            
        Returns:
            Dict with read results
        """
        result = await self.pool.execute_kw(
            model=model,
            method="read",
            args=[record_ids],
            kwargs={"fields": fields}
        )
        return {
            "records": result,
            "count": len(result)
        }

    async def create(
        self,
        model: str,
        values: Dict[str, Any],
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a record with validation and security.

        Args:
            model: Model name
            values: Record values
            operation_id: Operation ID for idempotency

        Returns:
            Dict with creation result
        """
        # Validate required fields
        fields_info = await self.schema_introspector.list_fields(user_id, model)
        missing_fields = []
        for field_name, field_info in fields_info.items():
            if field_info.required and field_name not in values:
                missing_fields.append(field_name)
        if missing_fields:
            raise Exception(f"Missing required fields: {', '.join(missing_fields)}")
        # Execute create
        result = await self.pool.execute_kw(
            model=model,
            method="create",
            args=[values]
        )
        return {
            "id": result,
            "operation_id": operation_id
        }

    async def write(
        self,
        model: str,
        record_ids: List[int],
        values: Dict[str, Any],
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write to records with validation and security.

        Args:
            model: Model name
            record_ids: List of record IDs
            values: Values to write
            operation_id: Operation ID for idempotency

        Returns:
            Dict with write result
        """
        result = await self.pool.execute_kw(
            model=model,
            method="write",
            args=[record_ids, values]
        )
        return {
            "success": result,
            "operation_id": operation_id
        }
