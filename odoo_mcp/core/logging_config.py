import logging
import sys
from typing import Dict, Any, Optional
import contextlib  # Add contextlib import
import os


def setup_logging(level: str = "INFO", protocol: str = "stdio") -> None:
    """
    Configure logging for the Odoo MCP Server.

    Args:
        level: Logging level (default: 'INFO')
        protocol: Server protocol ('stdio' or 'streamable_http')
    """
    # Remove any existing handlers from the root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure root logger
    root_logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create and configure stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    # If using stdio protocol, ensure no logs go to stdout
    if protocol == "stdio":
        # Create a null handler for stdout to prevent any logs from going there
        class StdoutNullHandler(logging.Handler):
            def emit(self, record):
                pass

        stdout_handler = StdoutNullHandler()
        stdout_handler.setFormatter(formatter)
        root_logger.addHandler(stdout_handler)

        # Disable propagation to prevent double logging
        root_logger.propagate = False

        # Log the configuration
        root_logger.info(f"Logging configured for stdio protocol. All logs will be written to stderr.")
    else:
        root_logger.info(f"Logging configured for {protocol} protocol.")

    # Configure specific loggers
    loggers = [
        "odoo_mcp",
        "odoo_mcp.core",
        "odoo_mcp.resources",
        "odoo_mcp.tools",
        "odoo_mcp.prompts",
        "odoo_mcp.performance",
        "odoo_mcp.error_handling",
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        # Ensure the logger uses the root logger's handlers
        logger.propagate = True
        logger.handlers = []

    # Configure logging for libraries if needed (e.g., reduce verbosity)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("cachetools").setLevel(logging.INFO)

    logging.info("Logging setup complete.")


def setup_logging_from_config(logging_config: dict):
    """
    Set up logging configuration from a logging config dictionary (as in config.json).
    Supports multiple handlers (StreamHandler, FileHandler) and custom formats.
    """
    import logging

    # Get logger for this module
    logger = logging.getLogger(__name__)

    try:
        logger.info("Starting logging configuration from config...")
        logger.debug(f"Logging config: {logging_config}")

        # Get root logger and set level
        root_logger = logging.getLogger()

        # Check environment variable first, then config file
        env_log_level = os.getenv("LOGGING_LEVEL", "").upper()
        config_log_level = logging_config.get("level", "INFO").upper()

        # Use environment variable if set, otherwise use config
        log_level = env_log_level if env_log_level else config_log_level

        logger.info(f"Environment LOGGING_LEVEL: {env_log_level}")
        logger.info(f"Config file log level: {config_log_level}")
        logger.info(f"Final log level set to: {log_level}")

        root_logger.setLevel(log_level)

        # Remove existing handlers
        logger.info("Removing existing handlers...")
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Configure handlers
        logger.info("Configuring handlers...")
        handlers = logging_config.get("handlers", [])
        logger.info(f"Found {len(handlers)} handlers to configure")

        if not handlers:
            logger.warning("No handlers found in config, adding default StreamHandler")
            # Add default StreamHandler if no handlers configured
            default_handler = logging.StreamHandler(sys.stderr)
            default_handler.setLevel(log_level)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] - %(message)s")
            default_handler.setFormatter(formatter)
            root_logger.addHandler(default_handler)
            logger.info("Default StreamHandler configured successfully")

        for handler_cfg in handlers:
            try:
                logger.info(f"Configuring handler of type: {handler_cfg['type']}")

                if handler_cfg["type"] == "StreamHandler":
                    logger.info("Creating StreamHandler...")
                    handler = logging.StreamHandler(sys.stderr)  # Explicitly use stderr
                elif handler_cfg["type"] == "FileHandler":
                    filename = handler_cfg.get("filename")
                    if not filename:
                        logger.error("FileHandler configured but no filename provided")
                        continue
                    logger.info(f"Creating FileHandler for file: {filename}")
                    try:
                        handler = logging.FileHandler(filename)
                    except Exception as e:
                        logger.error(f"Failed to create FileHandler for {filename}: {e}")
                        continue
                else:
                    logger.warning(f"Unsupported handler type: {handler_cfg['type']}")
                    continue

                # Set handler level
                handler_level = handler_cfg.get("level", log_level).upper()
                logger.info(f"Setting handler level to: {handler_level}")
                handler.setLevel(handler_level)

                # Create and set formatter
                log_format = handler_cfg.get(
                    "format",
                    logging_config.get("format", "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"),
                )
                logger.info(f"Using log format: {log_format}")
                formatter = logging.Formatter(log_format)
                handler.setFormatter(formatter)

                # Add handler to root logger
                root_logger.addHandler(handler)
                logger.info(f"Handler {handler_cfg['type']} configured successfully")

            except Exception as e:
                logger.error(f"Error configuring handler {handler_cfg.get('type', 'unknown')}: {e}")
                raise

        # Verify logging configuration
        logger.info("Verifying logging configuration...")
        logger.debug("This is a debug message - should be visible if DEBUG level is set")
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")

        logger.info("Logging configuration completed successfully")

    except Exception as e:
        logger.error(f"Failed to setup logging from config: {e}")
        # Fallback to basic logging configuration
        logger.info("Falling back to basic logging configuration...")
        setup_logging("INFO")
        raise
