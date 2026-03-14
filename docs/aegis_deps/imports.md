```mermaid
graph TD

agent_gate --> aegis_agent_classifier
agent_gate --> aegis_auth
agent_gate --> aegis_interfaces
agent_gate --> aegis_perception_screen_capture
agent_gate --> aegis_runtime_context
agent_gate --> aegis_runtime_screen_executor
agent_gate --> aegis_tools_declarations

computer_use --> agent_gate
computer_use --> aegis_perception_screen_capture

interfaces_voice --> agent_gate
interfaces_voice --> aegis_browser_manager
interfaces_voice --> aegis_computer_use
interfaces_voice --> aegis_interfaces
interfaces_voice --> aegis_perception_screen_capture
interfaces_voice --> aegis_perception_screen_ocr
interfaces_voice --> aegis_runtime_context
interfaces_voice --> aegis_runtime_screen_executor
interfaces_voice --> aegis_runtime_tool_manager
interfaces_voice --> aegis_tools_context
interfaces_voice --> aegis_tools_declarations

perception_screen_init --> aegis_perception_cursor
perception_screen_init --> aegis_perception_screen_capture
perception_screen_init --> aegis_perception_screen_type
perception_screen_init --> aegis_perception_window

perception_screen_capture --> aegis_perception_screen_som
perception_screen_capture --> aegis_perception_window

perception_screen_ocr --> aegis_tools_context

runtime_screen_executor --> aegis_perception_screen_capture
runtime_screen_executor --> aegis_tools
runtime_screen_executor --> aegis_tools_context
runtime_screen_executor --> aegis_tools_declarations

runtime_tool_manager --> aegis_tools_declarations

tools_init --> aegis_tools
tools_init --> aegis_tools_base

tools_browser_tools --> aegis_browser_manager
tools_browser_tools --> aegis_interfaces
tools_browser_tools --> aegis_tools_base

tools_context --> aegis_perception_screen_capture

tools_cursor_tools --> aegis_perception_cursor
tools_cursor_tools --> aegis_perception_screen_capture
tools_cursor_tools --> aegis_perception_screen_executor
tools_cursor_tools --> aegis_tools_base
tools_cursor_tools --> aegis_tools_context

tools_declarations --> aegis_tools_base

tools_keyboard_tools --> aegis_perception_screen_type
tools_keyboard_tools --> aegis_tools_base

tools_navigation_tools --> aegis_perception_cursor
tools_navigation_tools --> aegis_perception_window
tools_navigation_tools --> aegis_tools_base
tools_navigation_tools --> aegis_tools_context

tools_screen_tools --> aegis_perception_screen_capture
tools_screen_tools --> aegis_perception_screen_ocr
tools_screen_tools --> aegis_tools_base
tools_screen_tools --> aegis_tools_context
