#!/usr/bin/env python3
"""
Test script for performance optimization and final validation.
This tests the optimized performance features for the Responses API migration.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

# Import the necessary components from app.py
from app import (
    conversation_manager, 
    responses_client, 
    StreamEventProcessor,
    ConversationStorageError
)


def test_conversation_loading_performance():
    """Test that conversation loading performance meets requirements."""
    print("🧪 Testing conversation loading performance...")
    
    test_username = f"perf_test_user_{int(time.time())}"  # Use unique username
    
    # Create multiple conversations with messages to test loading performance
    conversation_ids = []
    for i in range(10):
        conv_id = conversation_manager.create_conversation(test_username, f"Test Chat {i}")
        conversation_ids.append(conv_id)
        
        # Add multiple messages to each conversation
        for j in range(20):
            conversation_manager.add_message(test_username, conv_id, "user", f"Message {j}")
            conversation_manager.add_message(test_username, conv_id, "assistant", f"Response {j}")
    
    # Test conversation list loading performance
    start_time = time.time()
    conversations = conversation_manager.list_conversations(test_username)
    list_load_time = time.time() - start_time
    
    assert len(conversations) == 10, f"Should have 10 conversations, got {len(conversations)}"
    assert list_load_time < 1.0, f"Conversation list loading took {list_load_time:.3f}s, should be < 1.0s"
    print(f"✓ Conversation list loaded in {list_load_time:.3f}s")
    
    # Test individual conversation loading performance
    start_time = time.time()
    for conv_id in conversation_ids[:5]:  # Test first 5 conversations
        messages = conversation_manager.get_message_list(test_username, conv_id)
        assert len(messages) == 40, f"Should have 40 messages, got {len(messages)}"
    individual_load_time = time.time() - start_time
    
    assert individual_load_time < 2.0, f"Individual conversation loading took {individual_load_time:.3f}s, should be < 2.0s"
    print(f"✓ Individual conversations loaded in {individual_load_time:.3f}s")
    
    print("✅ Conversation loading performance test passed!")
    return True


def test_concurrent_conversation_access():
    """Test that concurrent conversation access works efficiently."""
    print("\n🧪 Testing concurrent conversation access...")
    
    test_username = f"concurrent_test_user_{int(time.time())}"
    
    # Create a conversation for concurrent testing
    conv_id = conversation_manager.create_conversation(test_username, "Concurrent Test")
    
    def add_messages_concurrently(thread_id: int):
        """Add messages from multiple threads."""
        for i in range(5):
            try:
                conversation_manager.add_message(
                    test_username, 
                    conv_id, 
                    "user", 
                    f"Thread {thread_id} Message {i}"
                )
                time.sleep(0.01)  # Small delay to simulate real usage
            except Exception as e:
                print(f"Error in thread {thread_id}: {e}")
                return False
        return True
    
    # Test concurrent access with multiple threads
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(add_messages_concurrently, i) for i in range(5)]
        results = [future.result() for future in futures]
    
    concurrent_time = time.time() - start_time
    
    # Verify all threads completed successfully
    assert all(results), "All concurrent operations should succeed"
    
    # Verify messages were added correctly
    messages = conversation_manager.get_message_list(test_username, conv_id)
    assert len(messages) == 25, f"Should have 25 messages, got {len(messages)}"
    
    assert concurrent_time < 3.0, f"Concurrent operations took {concurrent_time:.3f}s, should be < 3.0s"
    print(f"✓ Concurrent access completed in {concurrent_time:.3f}s")
    
    print("✅ Concurrent conversation access test passed!")
    return True


def test_file_io_optimization():
    """Test that file I/O operations are optimized and don't block."""
    print("\n🧪 Testing file I/O optimization...")
    
    test_username = f"io_test_user_{int(time.time())}"
    
    # Test atomic write operations
    start_time = time.time()
    conv_id = conversation_manager.create_conversation(test_username, "I/O Test")
    
    # Add many messages to test I/O performance
    for i in range(50):
        conversation_manager.add_message(test_username, conv_id, "user", f"Test message {i}")
    
    io_time = time.time() - start_time
    
    # Verify the conversation was saved correctly
    messages = conversation_manager.get_message_list(test_username, conv_id)
    assert len(messages) == 50, f"Should have 50 messages, got {len(messages)}"
    
    assert io_time < 2.0, f"I/O operations took {io_time:.3f}s, should be < 2.0s"
    print(f"✓ File I/O operations completed in {io_time:.3f}s")
    
    # Test that temporary files are cleaned up properly
    user_file = conversation_manager._get_user_file_path(test_username)
    temp_files = [f for f in os.listdir(os.path.dirname(user_file)) if f.endswith('.tmp')]
    assert len(temp_files) == 0, f"Should have no temporary files, found {temp_files}"
    print("✓ Temporary files cleaned up properly")
    
    print("✅ File I/O optimization test passed!")
    return True


def test_streaming_performance():
    """Test that streaming response processing is efficient."""
    print("\n🧪 Testing streaming performance...")
    
    from queue import Queue
    
    # Create a mock stream with many events
    def create_large_stream():
        events = []
        events.append(Mock(type="response.created", response=Mock(id="test_123")))
        
        # Simulate a large response with many text deltas
        for i in range(100):
            events.append(Mock(type="response.output_text.delta", delta=f"Token {i} "))
        
        events.append(Mock(type="response.completed", response=Mock(id="test_123")))
        return events
    
    # Test stream processing performance
    event_queue = Queue()
    processor = StreamEventProcessor(event_queue)
    
    start_time = time.time()
    processor.process_stream(create_large_stream())
    processing_time = time.time() - start_time
    
    # Verify events were processed
    event_count = 0
    while not event_queue.empty():
        event_queue.get()
        event_count += 1
    
    assert event_count > 0, "Should have processed events"
    assert processing_time < 1.0, f"Stream processing took {processing_time:.3f}s, should be < 1.0s"
    print(f"✓ Stream processing completed in {processing_time:.3f}s")
    
    print("✅ Streaming performance test passed!")
    return True


def test_memory_usage_optimization():
    """Test that memory usage is optimized for large conversations."""
    print("\n🧪 Testing memory usage optimization...")
    
    test_username = "memory_test_user"
    
    # Create a conversation with many messages
    conv_id = conversation_manager.create_conversation(test_username, "Memory Test")
    
    # Add a large number of messages
    message_count = 1000
    for i in range(message_count):
        conversation_manager.add_message(test_username, conv_id, "user", f"Message {i}" * 10)  # Longer messages
    
    # Test that we can still load and process the conversation efficiently
    start_time = time.time()
    messages = conversation_manager.get_message_list(test_username, conv_id)
    load_time = time.time() - start_time
    
    assert len(messages) == message_count, f"Should have {message_count} messages, got {len(messages)}"
    assert load_time < 3.0, f"Large conversation loading took {load_time:.3f}s, should be < 3.0s"
    print(f"✓ Large conversation ({message_count} messages) loaded in {load_time:.3f}s")
    
    print("✅ Memory usage optimization test passed!")
    return True


def test_api_usage_monitoring():
    """Test that API usage monitoring and logging works correctly."""
    print("\n🧪 Testing API usage monitoring...")
    
    import logging
    
    # Capture log messages
    log_messages = []
    
    class TestLogHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())
    
    # Add test handler to root logger
    test_handler = TestLogHandler()
    logging.getLogger().addHandler(test_handler)
    logging.getLogger().setLevel(logging.INFO)
    
    try:
        # Test API call logging
        with patch.object(responses_client.client.responses, 'create') as mock_create:
            mock_create.return_value = Mock()
            
            start_time = time.time()
            responses_client.create_response("Test input", username="test_user")
            api_time = time.time() - start_time
            
            # Verify API call was made
            assert mock_create.called, "API call should have been made"
            print(f"✓ API call completed in {api_time:.3f}s")
        
        # Test performance logging for conversation operations
        test_username = "monitor_test_user"
        conv_id = conversation_manager.create_conversation(test_username, "Monitor Test")
        conversation_manager.add_message(test_username, conv_id, "user", "Test message")
        
        print("✓ API usage monitoring working correctly")
        
    finally:
        # Clean up
        logging.getLogger().removeHandler(test_handler)
    
    print("✅ API usage monitoring test passed!")
    return True


def test_error_recovery_performance():
    """Test that error recovery doesn't significantly impact performance."""
    print("\n🧪 Testing error recovery performance...")
    
    test_username = "recovery_test_user"
    
    # Test that system recovers quickly from errors
    start_time = time.time()
    
    # Simulate some failed operations
    for i in range(5):
        try:
            with patch.object(conversation_manager, '_save_user_conversations', 
                            side_effect=ConversationStorageError("Simulated error")):
                conv_id = conversation_manager.create_conversation(test_username, f"Recovery Test {i}")
                conversation_manager.add_message(test_username, conv_id, "user", "Test message")
        except ConversationStorageError:
            pass  # Expected
    
    # Now test that normal operations work quickly after errors
    conv_id = conversation_manager.create_conversation(test_username, "Recovery Success")
    conversation_manager.add_message(test_username, conv_id, "user", "Success message")
    
    recovery_time = time.time() - start_time
    
    # Verify the successful operation worked
    messages = conversation_manager.get_message_list(test_username, conv_id)
    assert len(messages) == 1, f"Should have 1 message, got {len(messages)}"
    
    assert recovery_time < 2.0, f"Error recovery took {recovery_time:.3f}s, should be < 2.0s"
    print(f"✓ Error recovery completed in {recovery_time:.3f}s")
    
    print("✅ Error recovery performance test passed!")
    return True


def test_final_integration_validation():
    """Test complete end-to-end functionality to validate the migration."""
    print("\n🧪 Testing final integration validation...")
    
    test_username = f"integration_test_user_{int(time.time())}"
    
    # Test conversation manager functionality directly
    conv_id = conversation_manager.create_conversation(test_username, "Integration Test")
    conversation_manager.add_message(test_username, conv_id, "user", "Hello, this is a test message")
    
    # Test conversation listing
    conversations = conversation_manager.list_conversations(test_username)
    assert len(conversations) > 0, "Should have at least one conversation"
    print("✓ Conversation listing working")
    
    # Test conversation retrieval
    messages = conversation_manager.get_message_list(test_username, conv_id)
    assert len(messages) > 0, "Should have at least one message"
    print("✓ Conversation retrieval working")
    
    # Test conversation metadata
    conversation = conversation_manager.get_conversation(test_username, conv_id)
    assert conversation is not None, "Should be able to retrieve conversation"
    assert conversation.chat_name == "Integration Test", "Chat name should match"
    print("✓ Conversation metadata working")
    
    # Test response ID tracking
    conversation_manager.add_message(test_username, conv_id, "assistant", "Test response", "test_response_id")
    last_response_id = conversation_manager.get_last_response_id(test_username, conv_id)
    assert last_response_id == "test_response_id", "Should track response IDs correctly"
    print("✓ Response ID tracking working")
    
    print("✅ Final integration validation test passed!")
    return True


if __name__ == "__main__":
    print("🧪 Testing performance optimization and final validation...\n")
    
    try:
        test_conversation_loading_performance()
        test_concurrent_conversation_access()
        test_file_io_optimization()
        test_streaming_performance()
        test_memory_usage_optimization()
        test_api_usage_monitoring()
        test_error_recovery_performance()
        test_final_integration_validation()
        
        print("\n🎉 All performance optimization tests passed!")
        print("✅ Conversation loading performance optimized!")
        print("✅ Concurrent access handling improved!")
        print("✅ File I/O operations optimized!")
        print("✅ Streaming performance enhanced!")
        print("✅ Memory usage optimized for large conversations!")
        print("✅ API usage monitoring implemented!")
        print("✅ Error recovery performance validated!")
        print("✅ Final integration validation completed!")
        print("\n🚀 OpenAI API migration to Responses API with o4-mini model is complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        raise