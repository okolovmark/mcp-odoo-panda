import logging

import httpx
from odoo_mcp.error_handling.exceptions import (
    AuthError,
    OdooMCPError,
    ProtocolError,
)

logger = logging.getLogger(__name__)


class JSONRPCHandler:
    """
    Handles communication with Odoo using the JSON-RPC protocol via HTTPX.

    Manages an asynchronous HTTP client session using `httpx.AsyncClient` and
    provides a method to execute RPC calls, incorporating caching for read operations.
    """

    def __init__(self, config: dict[str, str]):
        """
        Initialize the JSONRPCHandler.

        Sets up the base URL and an `httpx.AsyncClient` for making async HTTP calls.
        Uses the base class for common functionality.

        Args:
            config: The server configuration dictionary. Requires 'odoo_url', 'database'.
                    Optional TLS keys: 'tls_version', 'ca_cert_path',
                    'client_cert_path', 'client_key_path'.

        Raises:
            ConfigurationError: If TLS configuration fails.
        """
        self.config: dict[str, str] = config
        self.odoo_url: str = config["odoo_url"]
        self.database: str = config["database"]
        self.username: str = config["username"]
        self.password: str = config["password"]
        self.async_client = httpx.AsyncClient(timeout=int(config.get("timeout", 30)))
        self.jsonrpc_url: str = f"{self.odoo_url}/jsonrpc"
        self.uid = None

    def _prepare_payload(self, service: str, method: str, params: dict | list) -> dict:
        """Prepare the standard JSON-RPC 2.0 payload structure."""
        # For Odoo's JSON-RPC interface, we need to ensure params is a list
        if isinstance(params, dict):
            params = [params]
        elif not isinstance(params, list):
            params = [params]
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"service": service, "method": method, "args": params, "kwargs": {}},
            "id": None,
        }

    def _get_headers(self) -> dict[str, str]:
        """Get the headers for JSON-RPC requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OdooMCP/1.0",
        }

    async def ensure_authenticated(self):
        """Ensure we have a valid uid by authenticating if needed."""
        if self.uid is None:
            auth_result = await self.call(
                service="common",
                method="login",
                args=[self.database, self.username, self.password],
            )
            if not auth_result:
                raise AuthError(
                    f"Authentication failed: invalid credentials for database {self.database}"
                )
            self.uid = auth_result
        return self.uid

    async def call(self, service: str, method: str, args: list):
        """
        Execute a direct JSON-RPC call without caching.

        Args:
            service: The service name
            method: The method name
            args: The arguments to pass

        Returns:
            The result of the call
        """
        try:
            payload = self._prepare_payload(service, method, args)
            headers = self._get_headers()
            response = await self.async_client.post(self.jsonrpc_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("error"):
                error_data = result["error"]
                error_message = error_data.get("message", "Unknown JSON-RPC Error")
                error_code = error_data.get("code")
                error_debug_info = error_data.get("data", {}).get("debug", "")
                full_error = f"Code {error_code}: {error_message} - {error_debug_info}".strip(" -")
                raise ProtocolError(
                    f"JSON-RPC Error Response: {full_error}",
                    original_exception=Exception(str(error_data)),
                )
        except Exception as e:
            raise OdooMCPError(
                f"An unexpected error occurred during JSON-RPC call: {e}", original_exception=e
            )
        else:
            # Return the result directly without creating a Resource object
            return result.get("result")

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: list,
        kwargs: dict,
        uid: int | None = None,
        password: str | None = None,
        session_id: str | None = None,
    ):
        """
        Execute a method on an Odoo model using JSON-RPC 'object.execute_kw'.

        This method mirrors the XML-RPC execute_kw interface.

        Args:
            model: The Odoo model name.
            method: The method to call on the model.
            args: Positional arguments for the Odoo method.
            kwargs: Keyword arguments for the Odoo method. Should include 'context'.
            uid: User ID for authentication (required if password/session_id not used).
            password: Password or API key for authentication.
            session_id: Session ID to potentially include in the context.

        Returns:
            The result from the Odoo method.

        Raises:
            AuthError, NetworkError, ProtocolError, OdooMCPError, TypeError.
        """
        await self.ensure_authenticated()
        call_uid = uid if uid is not None else self.uid
        call_password = password if password is not None else self.password
        # Prepare context, merging session_id if provided
        context = kwargs.pop("context", {})
        if session_id:
            context["session_id"] = session_id
            logger.debug(f"Added session_id to context for JSON-RPC call {model}.{method}")
        # Arguments for Odoo's object.execute_kw: db, uid, password, model, method, args[, kwargs]
        odoo_args = [self.database, call_uid, call_password, model, method, args]
        if kwargs or context:  # Only add kwargs dict if it's not empty
            final_kwargs = kwargs.copy()
            if context:
                final_kwargs["context"] = context
            odoo_args.append(final_kwargs)
        return await self.call(service="object", method="execute_kw", args=odoo_args)

    async def cleanup(self) -> None:
        """Clean up JSON-RPC connections."""
        try:
            if hasattr(self, "async_client"):
                await self.async_client.aclose()
        except Exception as e:
            logger.warning(f"Error during JSONRPC cleanup: {e}")

    async def close(self):
        """Close the underlying httpx client session."""
        if hasattr(self, "async_client"):
            await self.async_client.aclose()
            logger.info("httpx.AsyncClient closed.")
