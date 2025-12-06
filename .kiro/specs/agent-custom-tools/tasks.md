# Implementation Plan

- [x] 1. Create tool framework infrastructure





  - Create `BaseTool` abstract base class with OpenAI best practices documentation
  - Create `ToolRegistry` class for managing available tools
  - Create `ToolInfo` dataclass for tool metadata
  - Implement tool registration and retrieval methods
  - Add built-in tool detection logic
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 2. Implement tool storage system





  - Create `ToolStorage` class for per-chat persistent storage
  - Implement get/set/delete/get_all/clear methods
  - Use `static/chats/{username}/{conversation_id}/{tool_name}.json` path structure
  - Integrate with existing `save_json_file_atomic` utility for atomic writes
  - Add thread-safe locking using `UserFileManager` pattern
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 3. Implement Calculator tool





  - Create `CalculatorTool` class extending `BaseTool`
  - Implement safe AST validation with allowed node types
  - Implement safe function whitelist (abs, min, max, round, sum, pow)
  - Create OpenAI function definition following best practices (strict schema, detailed descriptions)
  - Implement expression evaluation with error handling
  - Add calculation history storage (last 100 entries)
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 3.1 Write unit tests for Calculator tool






  - Test valid expressions: basic arithmetic, functions, parentheses
  - Test invalid expressions: malicious code, undefined functions, syntax errors
  - Test edge cases: division by zero, very large numbers, empty expressions
  - Test storage operations: history tracking, history limit
  - Test error handling: proper error messages for all failure modes
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 4. Create tool executor





  - Create `ToolExecutor` class for executing tool calls
  - Implement tool call routing to appropriate tool
  - Add comprehensive error handling for tool execution
  - Integrate with `ToolStorage` for per-chat data access
  - Add logging for tool execution events
  - _Requirements: 1.4, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 4.1 Write unit tests for tool executor
  - Test successful tool execution
  - Test tool not found error
  - Test invalid parameters error
  - Test tool execution exception handling
  - Test storage integration
  - _Requirements: 1.4, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5. Update AgentPreset model





  - Add `enabled_tools` field to `AgentPreset` Pydantic model
  - Set default value to `["web_search", "calculator"]`
  - Add field validator for tool names
  - Update agent preset API endpoints to handle enabled_tools
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ]* 5.1 Write unit tests for AgentPreset tool configuration
  - Test preset creation with default tools
  - Test preset creation with custom tools
  - Test tool name validation
  - Test empty tools list rejection
  - Test unknown tool name rejection
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 6. Extend ResponsesAPIClient for tool support





  - Add `enabled_tools` parameter to `create_response` method
  - Implement `_build_tools_array` method to construct tools from enabled_tools list
  - Handle built-in OpenAI tools (web_search with location config)
  - Handle custom tools (get definition from registry)
  - Update tool array construction to be dynamic based on preset
  - _Requirements: 1.4, 9.1, 9.2, 9.3, 9.4_

- [ ]* 6.1 Write unit tests for ResponsesAPIClient tool building
  - Test tools array with only web_search
  - Test tools array with only calculator
  - Test tools array with both tools
  - Test tools array with empty list
  - Test tools array with unknown tool (should skip)
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 7. Update chat endpoint for tool integration





  - Pass `enabled_tools` from agent preset to `ResponsesAPIClient`
  - Initialize tool registry at application startup
  - Register calculator tool in registry
  - Handle tool call events from OpenAI stream
  - Execute tools via `ToolExecutor` when requested
  - Return tool results to OpenAI API
  - _Requirements: 1.4, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 7.1 Write integration tests for tool execution flow
  - Test end-to-end calculator tool execution in chat
  - Test tool result incorporation in AI response
  - Test tool storage persistence across messages
  - Test error handling when tool execution fails
  - Test chat continues normally after tool errors
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 8. Update TypeScript interfaces for tools





  - Add `enabled_tools: string[]` field to `AgentPreset` interface
  - Update `AgentPresetFormData` interface with enabled_tools
  - Update agent preset API response types
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 9. Implement frontend tool configuration UI






  - Add tool configuration section to agent preset modal
  - Render built-in tools section with web_search checkbox
  - Render custom tools section with calculator checkbox
  - Implement tool toggle functionality
  - Update form data collection to include enabled_tools
  - Update preset save to send enabled_tools to backend
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ]* 9.1 Write frontend tests for tool configuration
  - Test tool checkboxes render correctly
  - Test tool toggle updates form state
  - Test preset save includes enabled_tools
  - Test preset load populates tool checkboxes
  - Test at least one tool must be enabled validation
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 10. Add tool configuration styling





  - Style tool configuration section in agent preset modal
  - Add visual distinction between built-in and custom tools
  - Style tool checkboxes and labels
  - Add hover states and accessibility features
  - Ensure responsive design for tool configuration
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Update documentation
  - Add tool framework documentation to README
  - Document how to create custom tools
  - Document OpenAI best practices for tool definitions
  - Add examples of tool usage
  - Document tool storage structure
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
