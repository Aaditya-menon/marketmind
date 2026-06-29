import logging
from typing import Any

logger = logging.getLogger("marketmind.tools.mcp_config")

class MCPConnectionManager:
    """Placeholder connection manager since all tools have migrated to direct REST APIs."""
    
    async def get_session(self, server_id: str) -> Any:
        raise ValueError(f"MCP servers have been disabled. Server '{server_id}' is not available.")
        
    async def close_all(self):
        pass

# Singleton connection manager placeholder to keep imports valid
mcp_manager = MCPConnectionManager()
