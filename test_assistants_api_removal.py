#!/usr/bin/env python3
"""
Test script to verify that all Assistants API dependencies have been removed.
This test ensures the migration is complete and no old API code remains.
"""

import re

# Import the app to test
import app


def test_imports_cleanup():
    """Test that all Assistants API imports have been removed."""
    print("🧪 Testing Assistants API imports cleanup...")
    
    # Read the app.py file to check imports
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # Check for removed imports (excluding comments and docstrings)
    import_lines = [line for line in app_content.split('\n') if line.strip().startswith(('import ', 'from '))]
    import_content = '\n'.join(import_lines)
    
    removed_imports = [
        'AssistantEventHandler',
        'from openai.types.beta.threads import',
        'from openai.types.beta.threads.run_submit_tool_outputs_params import',
        'from openai.types.beta.threads.runs import',
        'Text,',
        'TextContentBlock,',
        'TextDelta',
        'ToolOutput',
        'FunctionToolCall,',
        'ToolCall,',
        'ToolCallDelta'
    ]
    
    for import_item in removed_imports:
        assert import_item not in import_content, f"Found removed import still present: {import_item}"
    
    print("✓ All Assistants API imports successfully removed")
    
    # Check that only necessary imports remain
    required_imports = [
        'from openai.types.responses.response_stream_event import ResponseStreamEvent'
    ]
    
    for required_import in required_imports:
        assert required_import in app_content, f"Required import missing: {required_import}"
    
    print("✓ Required Responses API imports present")
    print("✅ Imports cleanup test passed!")
    return True


def test_classes_cleanup():
    """Test that Assistants API classes have been removed."""
    print("\n🧪 Testing Assistants API classes cleanup...")
    
    # Read the app.py file to check for removed classes
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # Check that StreamingEventHandler class is removed
    assert 'class StreamingEventHandler' not in app_content, "StreamingEventHandler class still present"
    print("✓ StreamingEventHandler class successfully removed")
    
    # Check that StreamEventProcessor class is still present
    assert 'class StreamEventProcessor' in app_content, "StreamEventProcessor class missing"
    print("✓ StreamEventProcessor class present (correct replacement)")
    
    # Verify no code references to AssistantEventHandler remain (excluding comments/docstrings)
    code_lines = [line for line in app_content.split('\n') 
                  if not line.strip().startswith('#') 
                  and not line.strip().startswith('"""')
                  and not line.strip().startswith("'''")
                  and '"""' not in line.strip()]
    code_content = '\n'.join(code_lines)
    
    # Allow references in docstrings but not in actual code
    assistant_handler_in_code = 'AssistantEventHandler(' in code_content or 'extends AssistantEventHandler' in code_content
    assert not assistant_handler_in_code, "AssistantEventHandler code references still present"
    print("✓ No AssistantEventHandler code references remain (documentation references OK)")
    
    print("✅ Classes cleanup test passed!")
    return True


def test_api_calls_cleanup():
    """Test that all Assistants API calls have been removed."""
    print("\n🧪 Testing Assistants API calls cleanup...")
    
    # Read the app.py file to check for API calls
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # Check for removed API calls
    removed_api_calls = [
        'client.beta.threads',
        'client.beta.messages',
        'client.beta.runs',
        'client.beta.assistants',
        'submit_tool_outputs',
        'threads.create',
        'threads.retrieve',
        'messages.create',
        'messages.list',
        'runs.stream'
    ]
    
    for api_call in removed_api_calls:
        assert api_call not in app_content, f"Found removed API call still present: {api_call}"
    
    print("✓ All Assistants API calls successfully removed")
    
    # Check that Responses API calls are present
    responses_api_calls = [
        'client.responses.create',
        'responses_client.create_response'
    ]
    
    for api_call in responses_api_calls:
        assert api_call in app_content, f"Required Responses API call missing: {api_call}"
    
    print("✓ Responses API calls present")
    print("✅ API calls cleanup test passed!")
    return True


def test_functions_cleanup():
    """Test that Assistants API functions have been removed."""
    print("\n🧪 Testing Assistants API functions cleanup...")
    
    # Read the app.py file to check for removed functions
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # Check that process_tool_output function is removed
    assert 'def process_tool_output' not in app_content, "process_tool_output function still present"
    print("✓ process_tool_output function successfully removed")
    
    # Check that old get_message_list function is removed
    assert 'client.beta.threads.messages.list' not in app_content, "Old get_message_list function still present"
    print("✓ Old get_message_list function successfully removed")
    
    # Verify ConversationManager methods are present
    conversation_manager_methods = [
        'conversation_manager.create_conversation',
        'conversation_manager.add_message',
        'conversation_manager.get_message_list',
        'conversation_manager.get_last_response_id'
    ]
    
    for method in conversation_manager_methods:
        assert method in app_content, f"Required ConversationManager method missing: {method}"
    
    print("✓ ConversationManager methods present")
    print("✅ Functions cleanup test passed!")
    return True


def test_variable_references_cleanup():
    """Test that assistant_id and thread_id references have been cleaned up."""
    print("\n🧪 Testing variable references cleanup...")
    
    # Read the app.py file to check for variable references
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # Check for removed variable references (excluding comments)
    lines = app_content.split('\n')
    code_lines = [line for line in lines if not line.strip().startswith('#')]
    code_content = '\n'.join(code_lines)
    
    # These should not appear in actual code (excluding comments)
    removed_variables = [
        'assistant_id =',
        'thread_id =',
        'run_id =',
        'thread.id',
        'assistant.id'
    ]
    
    for variable in removed_variables:
        assert variable not in code_content, f"Found removed variable still present: {variable}"
    
    print("✓ Assistant and thread ID references successfully removed")
    
    # Check that conversation_id is used instead
    assert 'conversation_id' in app_content, "conversation_id variable missing"
    print("✓ conversation_id variable present (correct replacement)")
    
    print("✅ Variable references cleanup test passed!")
    return True


def test_app_functionality():
    """Test that the app still functions correctly after cleanup."""
    print("\n🧪 Testing app functionality after cleanup...")
    
    # Test that key components are still accessible
    assert hasattr(app, 'conversation_manager'), "ConversationManager missing"
    assert hasattr(app, 'responses_client'), "ResponsesAPIClient missing"
    assert hasattr(app, 'StreamEventProcessor'), "StreamEventProcessor missing"
    print("✓ Key components accessible")
    
    # Test that the app can be imported without errors
    assert app.app is not None, "Flask app not accessible"
    print("✓ Flask app accessible")
    
    # Test that ConversationManager works
    test_username = "cleanup_test_user"
    conversation_id = app.conversation_manager.create_conversation(test_username, "Cleanup Test")
    assert conversation_id is not None, "ConversationManager not working"
    print("✓ ConversationManager functional")
    
    # Test that ResponsesAPIClient is configured correctly
    assert app.responses_client.model == "o4-mini", f"Expected o4-mini, got {app.responses_client.model}"
    print("✓ ResponsesAPIClient configured correctly")
    
    print("✅ App functionality test passed!")
    return True


def test_migration_completeness():
    """Test that the migration is complete and comprehensive."""
    print("\n🧪 Testing migration completeness...")
    
    # Read the app.py file for final verification
    with open('app.py', 'r', encoding='utf-8') as f:
        app_content = f.read()
    
    # Count occurrences of old vs new patterns
    old_patterns = [
        'AssistantEventHandler',
        'client.beta',
        'thread_id',
        'assistant_id',
        'run_id'
    ]
    
    new_patterns = [
        'StreamEventProcessor',
        'client.responses',
        'conversation_id',
        'response_id',
        'ConversationManager'
    ]
    
    # Check that old patterns are minimal (only in comments/strings)
    for pattern in old_patterns:
        occurrences = len(re.findall(pattern, app_content))
        # Allow some occurrences in comments and variable names
        assert occurrences <= 5, f"Too many occurrences of old pattern '{pattern}': {occurrences}"
    
    print("✓ Old patterns minimized")
    
    # Check that new patterns are present
    for pattern in new_patterns:
        occurrences = len(re.findall(pattern, app_content))
        assert occurrences > 0, f"New pattern '{pattern}' not found"
    
    print("✓ New patterns present")
    
    # Verify the migration is using the correct API
    assert 'o4-mini' in app_content, "o4-mini model not configured"
    assert 'previous_response_id' in app_content, "Conversation continuity not implemented"
    print("✓ Migration using correct API and model")
    
    print("✅ Migration completeness test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing Assistants API dependencies removal...\n")
    
    try:
        test_imports_cleanup()
        test_classes_cleanup()
        test_api_calls_cleanup()
        test_functions_cleanup()
        test_variable_references_cleanup()
        test_app_functionality()
        test_migration_completeness()
        
        print("\n🎉 All Assistants API removal tests passed!")
        print("✅ All Assistants API dependencies successfully removed!")
        print("✅ Migration to Responses API is complete!")
        print("✅ System functionality preserved!")
        print("✅ Code cleanup comprehensive!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise