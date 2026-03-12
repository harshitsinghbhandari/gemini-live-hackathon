from .base import registry

# This will eventually hold all declarations if we don't want to import tool classes every time
# But for now, we will use it to export SCREEN_TOOL_DECLARATIONS for backwards compatibility.

def get_screen_tool_declarations():
    all_decls = registry.get_all_declarations()
    # Explicitly include all registered tools in the schema
    return all_decls
