```mermaid
graph LR

%%--------------------
%% Subgraphs
%%--------------------
subgraph Agent
    agent_gate["agent.gate"]
end

subgraph Aegis_Core
    aegis_agent_classifier["aegis.agent.classifier"]
    aegis_auth["aegis.auth"]
    aegis_interfaces["aegis.interfaces"]
    aegis_runtime_context["aegis.runtime.context"]
    aegis_runtime_screen_executor["aegis.runtime.screen_executor"]
    aegis_runtime_tool_manager["aegis.runtime.tool_manager"]
    aegis_tools["aegis.tools"]
    aegis_tools_declarations["aegis.tools.declarations"]
end

subgraph Interfaces
    interfaces_voice["interfaces.voice"]
    aegis_browser_manager["aegis.browser_manager"]
    aegis_computer_use["aegis.computer_use"]
end

subgraph Perception
    perception_screen_init["perception.screen.__init__"]
    perception_screen_capture["perception.screen.capture"]
    perception_screen_ocr["perception.screen.ocr"]
    perception_cursor["aegis.perception.cursor"]
    perception_screen_type["aegis.perception.screen.type"]
    perception_window["aegis.perception.window"]
    perception_screen_som["aegis.perception.screen.som"]
end

subgraph Tools
    tools_init["tools.__init__"]
    tools_browser_tools["tools.browser_tools"]
    tools_context["tools.context"]
    tools_cursor_tools["tools.cursor_tools"]
    tools_declarations["tools.declarations"]
    tools_keyboard_tools["tools.keyboard_tools"]
    tools_navigation_tools["tools.navigation_tools"]
    tools_screen_tools["tools.screen_tools"]
end

%%--------------------
%% Connections
%%--------------------

%% Agent connections
agent_gate --> aegis_agent_classifier
agent_gate --> aegis_auth
agent_gate --> aegis_interfaces
agent_gate --> perception_screen_capture
agent_gate --> aegis_runtime_context
agent_gate --> aegis_runtime_screen_executor
agent_gate --> aegis_tools_declarations

%% Computer use connections
aegis_computer_use --> agent_gate
aegis_computer_use --> perception_screen_capture

%% Interfaces connections
interfaces_voice --> agent_gate
interfaces_voice --> aegis_browser_manager
interfaces_voice --> aegis_computer_use
interfaces_voice --> aegis_interfaces
interfaces_voice --> perception_screen_capture
interfaces_voice --> perception_screen_ocr
interfaces_voice --> aegis_runtime_context
interfaces_voice --> aegis_runtime_screen_executor
interfaces_voice --> aegis_runtime_tool_manager
interfaces_voice --> tools_context
interfaces_voice --> aegis_tools_declarations

%% Perception connections
perception_screen_init --> perception_cursor
perception_screen_init --> perception_screen_capture
perception_screen_init --> perception_screen_type
perception_screen_init --> perception_window

perception_screen_capture --> perception_screen_som
perception_screen_capture --> perception_window
perception_screen_ocr --> tools_context

%% Runtime connections
aegis_runtime_screen_executor --> perception_screen_capture
aegis_runtime_screen_executor --> aegis_tools
aegis_runtime_screen_executor --> tools_context
aegis_runtime_screen_executor --> aegis_tools_declarations
aegis_runtime_tool_manager --> aegis_tools_declarations

%% Tools connections
tools_init --> aegis_tools
tools_init --> aegis_tools_declarations
tools_browser_tools --> aegis_browser_manager
tools_browser_tools --> aegis_interfaces
tools_browser_tools --> aegis_tools_declarations
tools_context --> perception_screen_capture
tools_cursor_tools --> perception_cursor
tools_cursor_tools --> perception_screen_capture
tools_cursor_tools --> aegis_runtime_screen_executor
tools_cursor_tools --> aegis_tools_declarations
tools_cursor_tools --> tools_context
tools_declarations --> aegis_tools_declarations
tools_keyboard_tools --> perception_screen_type
tools_keyboard_tools --> aegis_tools_declarations
tools_navigation_tools --> perception_cursor
tools_navigation_tools --> perception_window
tools_navigation_tools --> aegis_tools_declarations
tools_navigation_tools --> tools_context
tools_screen_tools --> perception_screen_capture
tools_screen_tools --> perception_screen_ocr
tools_screen_tools --> aegis_tools_declarations
tools_screen_tools --> tools_context

%%--------------------
%% Styling
%%--------------------
style Agent fill:#f9f,stroke:#333,stroke-width:2px
style Aegis_Core fill:#9cf,stroke:#333,stroke-width:2px
style Interfaces fill:#fc9,stroke:#333,stroke-width:2px
style Perception fill:#c9f,stroke:#333,stroke-width:2px
style Tools fill:#9fc,stroke:#333,stroke-width:2px