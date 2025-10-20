"""
Capabilities Manager implementation for Odoo MCP Server.
This module provides capability management.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Resource types supported by the server."""

    MODEL = "model"
    BINARY = "binary"
    LIST = "list"
    RECORD = "record"


@dataclass
class ResourceTemplate:
    """Resource template definition."""

    name: str
    type: ResourceType
    description: str
    operations: list[str]
    parameters: dict[str, Any] | None = None


@dataclass
class Tool:
    """Tool definition."""

    name: str
    description: str
    operations: list[str]
    parameters: dict[str, Any] | None = None
    inputSchema: dict[str, Any] | None = None


@dataclass
class Prompt:
    """Prompt definition."""

    name: str
    description: str
    template: str
    parameters: dict[str, Any] | None = None


class CapabilitiesManager:
    """Manages server capabilities and feature flags."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize capabilities manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.resources: dict[str, ResourceTemplate] = {}
        self.tools: dict[str, Tool] = {}
        self.prompts: dict[str, Prompt] = {}

        # Register default capabilities
        self._register_resources()
        self._register_tools()

    def _register_resources(self) -> None:
        """Register default server resources."""
        # Register resource templates
        self.register_resource(
            ResourceTemplate(
                name="res.partner",
                type=ResourceType.MODEL,
                description="Odoo Partner/Contact resource",
                operations=["create", "read", "update", "delete", "search"],
                parameters={
                    "uri_template": "odoo://{model}/{id}",
                    "list_uri_template": "odoo://{model}/list",
                    "binary_uri_template": "odoo://{model}/binary/{field}/{id}",
                },
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="res.users",
                type=ResourceType.MODEL,
                description="Odoo User resource",
                operations=["create", "read", "update", "delete", "search"],
                parameters={
                    "uri_template": "odoo://{model}/{id}",
                    "list_uri_template": "odoo://{model}/list",
                    "binary_uri_template": "odoo://{model}/binary/{field}/{id}",
                },
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="product.product",
                type=ResourceType.MODEL,
                description="Odoo Product resource",
                operations=["create", "read", "update", "delete", "search"],
                parameters={
                    "uri_template": "odoo://{model}/{id}",
                    "list_uri_template": "odoo://{model}/list",
                    "binary_uri_template": "odoo://{model}/binary/{field}/{id}",
                },
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="sale.order",
                type=ResourceType.MODEL,
                description="Odoo Sales Order resource",
                operations=["create", "read", "update", "delete", "search"],
                parameters={
                    "uri_template": "odoo://{model}/{id}",
                    "list_uri_template": "odoo://{model}/list",
                    "binary_uri_template": "odoo://{model}/binary/{field}/{id}",
                },
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="ir.attachment",
                type=ResourceType.BINARY,
                description="Odoo Attachment resource",
                operations=["create", "read", "update", "delete"],
                parameters={
                    "uri_template": "odoo://{model}/{id}",
                    "binary_uri_template": "odoo://{model}/binary/{field}/{id}",
                },
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="Odoo Record",
                type=ResourceType.RECORD,
                description="Represents a single record in an Odoo model",
                operations=["read", "write", "delete"],
                parameters={
                    "uri_template": "odoo://{model}/{id}",
                    "list_uri_template": "odoo://{model}/list",
                    "binary_uri_template": "odoo://{model}/binary/{field}/{id}",
                },
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="Odoo Record List",
                type=ResourceType.LIST,
                description="Represents a list of records in an Odoo model",
                operations=["read", "search"],
                parameters={"uri_template": "odoo://{model}/list"},
            )
        )

        self.register_resource(
            ResourceTemplate(
                name="Odoo Binary Field",
                type=ResourceType.BINARY,
                description="Represents a binary field value from an Odoo record",
                operations=["read", "write"],
                parameters={"uri_template": "odoo://{model}/binary/{field}/{id}"},
            )
        )

    def _register_tools(self) -> None:
        """Register tools for Odoo ORM operations."""
        
        def create_input_schema(parameters: dict[str, Any]) -> dict[str, Any]:
            """Convert parameters dict to proper JSON Schema inputSchema format."""
            properties = {}
            required = []

            for param_name, param_def in parameters.items():
                # Skip 'optional' fields and other metadata
                if param_name in ['optional', 'default']:
                    continue

                param_schema = {}
                if 'type' in param_def:
                    param_schema['type'] = param_def['type']
                if 'description' in param_def:
                    param_schema['description'] = param_def['description']
                if 'items' in param_def:
                    param_schema['items'] = param_def['items']
                properties[param_name] = param_schema

                # Add to required if not optional and no default
                if not param_def.get('optional', False) and 'default' not in param_def:
                    required.append(param_name)

            return {
                "type": "object",
                "properties": properties,
                "required": required
            }
        
        # Define tool parameters
        tool_definitions = [
            {
                "name": "odoo_schema_version",
                "description": "Get the current schema version using global authentication",
                "operations": ["read"],
                "parameters": {}
            },
            {
                "name": "odoo_execute_kw",
                "description": "Execute an arbitrary method on an Odoo model",
                "operations": ["execute"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "method": {"type": "string", "description": "Method name to execute"},
                    "args": {"type": "array", "description": "Positional arguments for the method", "optional": True},
                    "kwargs": {"type": "object", "description": "Keyword arguments for the method", "optional": True},
                },
            },
            {
                "name": "odoo_unlink",
                "description": "Delete records from an Odoo model",
                "operations": ["unlink"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "ids": {"type": "array", "items": {"type": "integer"}, "description": "List of record IDs to delete"}
                },
            },
            {
                "name": "odoo_schema_models",
                "description": "List accessible models using global authentication",
                "operations": ["read"],
                "parameters": {
                    "with_access": {"type": "boolean", "description": "Whether to filter by access rights", "default": True}
                }
            },
            {
                "name": "odoo_schema_fields",
                "description": "Get fields for a specific model using global authentication",
                "operations": ["read"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"}
                }
            },
            {
                "name": "odoo_search_read",
                "description": "Search and read records with security enhancements using global authentication",
                "operations": ["read"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "domain_json": {"type": "object", "description": "Search domain in JSON format", "optional": True},
                    "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to retrieve", "optional": True},
                    "limit": {"type": "integer", "description": "Maximum number of records", "default": 50},
                    "offset": {"type": "integer", "description": "Number of records to skip", "default": 0},
                    "order": {"type": "string", "description": "Order specification", "optional": True}
                }
            },
            {
                "name": "odoo_name_search",
                "description": "Search records by name with security using global authentication",
                "operations": ["read"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "name": {"type": "string", "description": "Name to search for"},
                    "operator": {"type": "string", "description": "Search operator", "default": "ilike"},
                    "limit": {"type": "integer", "description": "Maximum number of results", "default": 10}
                }
            },
            {
                "name": "odoo_read",
                "description": "Read records with security using global authentication",
                "operations": ["read"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "record_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of record IDs"},
                    "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to retrieve", "optional": True}
                }
            },
            {
                "name": "odoo_create",
                "description": "Create a record with validation and security using global authentication",
                "operations": ["create"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "values": {"type": "object", "description": "Record values"},
                    "operation_id": {"type": "string", "description": "Operation ID for idempotency", "optional": True}
                }
            },
            {
                "name": "odoo_write",
                "description": "Write to records with validation and security using global authentication",
                "operations": ["update"],
                "parameters": {
                    "model": {"type": "string", "description": "Model name"},
                    "record_ids": {"type": "array", "items": {"type": "integer"}, "description": "List of record IDs"},
                    "values": {"type": "object", "description": "Values to write"},
                    "operation_id": {"type": "string", "description": "Operation ID for idempotency", "optional": True}
                }
            }
        ]

        # Create Tool objects with proper inputSchema
        orm_tools = []
        for tool_def in tool_definitions:
            orm_tools.append(Tool(
                name=tool_def["name"],
                description=tool_def["description"],
                operations=tool_def["operations"],
                parameters=tool_def["parameters"],
                inputSchema=create_input_schema(tool_def["parameters"])
            ))

        for tool in orm_tools:
            logger.info(f"Registering ORM tool: {tool.name}")
            self.register_tool(tool)
            logger.info(f"ORM tool {tool.name} registered successfully")


    def register_resource(self, resource: ResourceTemplate) -> None:
        """
        Register a resource template.

        Args:
            resource: Resource template to register
        """
        self.resources[resource.name] = resource
        logger.info(f"Registered resource: {resource.name}")

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def register_prompt(self, prompt: Prompt) -> None:
        """
        Register a prompt.

        Args:
            prompt: Prompt to register
        """
        self.prompts[prompt.name] = prompt
        logger.info(f"Registered prompt: {prompt.name}")

    def get_resource(self, name: str) -> ResourceTemplate | None:
        """
        Get a resource template by name.

        Args:
            name: Name of the resource

        Returns:
            Optional[ResourceTemplate]: Resource template if found, None otherwise
        """
        return self.resources.get(name)

    def get_tool(self, name: str) -> Tool | None:
        """
        Get a tool by name.

        Args:
            name: Name of the tool

        Returns:
            Optional[Tool]: Tool if found, None otherwise
        """
        return self.tools.get(name)

    def list_resources(self) -> list[dict[str, Any]]:
        """
        list all registered resources.

        Returns:
            list[dict[str, Any]]: list of resource templates as dictionaries with the following structure:
            {
                "name": str,
                "type": str,
                "description": str,
                "operations": list[str],
                "parameters": dict[str, Any] | None,
                "uri": str  # Required field for MCP client
            }
        """
        return [
            {
                "name": resource.name,
                "type": resource.type.value,
                "description": resource.description,
                "operations": resource.operations,
                "parameters": resource.parameters or {},
                "uri": f"odoo://{resource.name}",  # Add URI field in odoo:// format
            }
            for resource in self.resources.values()
        ]

    def list_tools(self) -> list[dict[str, Any]]:
        """
        list all registered tools.

        Returns:
            list[dict[str, Any]]: list of tool objects with the following structure:
            {
                "name": str,
                "description": str,
                "operations": list[str],
                "parameters": dict[str, Any] | None,
                "inputSchema": dict[str, Any]
            }
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "operations": tool.operations,
                "parameters": tool.parameters or {},
                "inputSchema": tool.inputSchema
                or {"type": "object", "properties": {}, "required": []},
            }
            for tool in self.tools.values()
        ]

    def list_prompts(self) -> list[dict[str, Any]]:
        """
        list all registered prompts.

        Returns:
            list[dict[str, Any]]: list of prompt objects with the following structure:
            {
                "name": str,
                "description": str,
                "template": str,
                "parameters": dict[str, Any] | None
            }
        """
        return [
            {
                "name": prompt.name,
                "description": prompt.description,
                "template": prompt.template,
                "parameters": prompt.parameters or {},
            }
            for prompt in self.prompts.values()
        ]

    def list_resource_templates(self) -> list[dict[str, Any]]:
        """
        list all registered resource templates.

        Returns:
            list[dict[str, Any]]: list of resource templates with the following structure:
            {
                "name": str,
                "type": str,
                "description": str,
                "operations": list[str],
                "parameters": dict[str, Any] | None,
                "uriTemplate": str
            }
        """
        return [
            {
                "name": resource.name,
                "type": resource.type.value,
                "description": resource.description,
                "operations": resource.operations,
                "parameters": resource.parameters or {},
                "uriTemplate": (resource.parameters or {}).get("uri_template", f"odoo://{resource.name}"),
            }
            for resource in self.resources.values()
        ]

    def get_capabilities(self) -> dict[str, Any]:
        """
        Get server capabilities following MCP 2025-03-26 specification.
        """
        return {
            "logging": {},
            "prompts": {"listChanged": True},
            "resources": {"subscribe": True, "listChanged": True},
            "tools": {"listChanged": True},
        }
