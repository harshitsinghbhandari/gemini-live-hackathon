from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger("aegis.tools.base")

class BaseTool(ABC):
    """Abstract base class for all Aegis tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass

    @property
    @abstractmethod
    def declaration(self) -> Dict[str, Any]:
        """The Gemini function declaration for this tool."""
        pass

    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass

class ToolRegistry:
    """Registry to manage and dispatch tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a new tool."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a tool by name."""
        return self._tools.get(name)

    def get_all_declarations(self) -> List[Dict[str, Any]]:
        """Get declarations for all registered tools."""
        return [tool.declaration for tool in self._tools.values()]

    async def dispatch(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch execution to the named tool."""
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' not found."}
        
        try:
            return await tool.execute(args)
        except Exception as e:
            logger.exception(f"Error executing tool '{name}': {e}")
            return {"success": False, "error": f"Internal execution error: {str(e)}"}

# Global registry instance
registry = ToolRegistry()
