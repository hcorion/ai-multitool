#!/usr/bin/env python3
"""
Unit tests for ConversationManager title update functionality.
Tests the update_conversation_title method with various scenarios.
"""

import os
import tempfile
import shutil
from unittest.mock import patch
import json

# Set a dummy API key for testing to avoid initialization errors
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-unit-tests")

# Import the ConversationManager class from app.py
from app import ConversationManager, ConversationStorageError


def test_conversation_manager_title_update_method_exists():
    """Test ConversationManager has title update method."""
    print("\n🧪 Testing ConversationManager title update method exists...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        assert hasattr(conversation_manager, "update_conversation_title"), (
            "Should have update_conversation_title method"
        )
        assert callable(conversation_manager.update_conversation_title), (
            "update_conversation_title should be callable"
        )

    print("✓ ConversationManager has title update method")


def test_successful_title_update():
    """Test successful conversation title update."""
    print("\n🧪 Testing successful title update...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        test_chat_name = "Original Title"
        conversation_id = conversation_manager.create_conversation(
            test_username, test_chat_name
        )

        # Verify original title (create_conversation allows spaces)
        conversation = conversation_manager.get_conversation(
            test_username, conversation_id
        )
        assert conversation is not None, "Conversation should exist"
        assert conversation.chat_name == "Original Title", (
            f"Expected 'Original Title', got '{conversation.chat_name}'"
        )
        original_last_update = conversation.last_update

        # Add small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Update the title
        new_title = "Updated Title"
        result = conversation_manager.update_conversation_title(
            test_username, conversation_id, new_title
        )

        assert result == True, "Title update should succeed"

        # Verify the title was updated (update_conversation_title also allows spaces)
        updated_conversation = conversation_manager.get_conversation(
            test_username, conversation_id
        )
        assert updated_conversation is not None, "Updated conversation should exist"
        assert updated_conversation.chat_name == "Updated Title", (
            f"Expected 'Updated Title', got '{updated_conversation.chat_name}'"
        )

        # Verify last_update timestamp was updated
        assert updated_conversation.last_update >= original_last_update, (
            "last_update should be same or newer"
        )

    print("✓ Successful title update works correctly")


def test_title_sanitization():
    """Test title sanitization during update."""
    print("\n🧪 Testing title sanitization...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(
            test_username, "Original"
        )

        # Test various title sanitization scenarios
        test_cases = [
            ("Title with @#$% special chars", "Title with ____ special chars"),
            ("   Whitespace Title   ", "Whitespace Title"),
            ("Title/with\\slashes", "Title_with_slashes"),
            (
                "Very Long Title That Exceeds Thirty Characters Limit",
                "Very Long Title That Exceeds T",
            ),
            ("Normal Title", "Normal Title"),
        ]

        for input_title, expected_output in test_cases:
            result = conversation_manager.update_conversation_title(
                test_username, conversation_id, input_title
            )
            assert result == True, f"Title update should succeed for: {input_title}"

            conversation = conversation_manager.get_conversation(
                test_username, conversation_id
            )
            assert conversation.chat_name == expected_output, (
                f"Expected '{expected_output}', got '{conversation.chat_name}' for input '{input_title}'"
            )

    print("✓ Title sanitization works correctly")


def test_nonexistent_conversation():
    """Test updating title for nonexistent conversation."""
    print("\n🧪 Testing nonexistent conversation handling...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Try to update title for nonexistent conversation
        fake_conversation_id = "fake-conversation-id"
        result = conversation_manager.update_conversation_title(
            "test_user", fake_conversation_id, "New Title"
        )

        assert result == False, "Should return False for nonexistent conversation"

    print("✓ Nonexistent conversation handling works correctly")


def test_invalid_title_validation():
    """Test validation of invalid titles."""
    print("\n🧪 Testing invalid title validation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(
            test_username, "Original"
        )

        # Test invalid title scenarios
        invalid_titles = [
            "",  # Empty string
            None,  # None value
            123,  # Non-string type
            [],  # List type
            {},  # Dict type
        ]

        for invalid_title in invalid_titles:
            result = conversation_manager.update_conversation_title(
                test_username, conversation_id, invalid_title
            )
            assert result == False, (
                f"Should return False for invalid title: {invalid_title}"
            )

            # Verify original title is unchanged
            conversation = conversation_manager.get_conversation(
                test_username, conversation_id
            )
            assert conversation.chat_name == "Original", (
                f"Original title should be preserved, got '{conversation.chat_name}'"
            )

    print("✓ Invalid title validation works correctly")


def test_storage_error_handling():
    """Test handling of storage errors during title update."""
    print("\n🧪 Testing storage error handling...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(
            test_username, "Original"
        )

        # Mock a storage error
        with patch.object(
            conversation_manager, "_save_user_conversations"
        ) as mock_save:
            mock_save.side_effect = ConversationStorageError("Simulated storage error")

            result = conversation_manager.update_conversation_title(
                test_username, conversation_id, "New Title"
            )
            assert result == False, "Should return False when storage error occurs"

    print("✓ Storage error handling works correctly")


def test_general_exception_handling():
    """Test handling of general exceptions during title update."""
    print("\n🧪 Testing general exception handling...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(
            test_username, "Original"
        )

        # Mock a general exception
        with patch.object(
            conversation_manager, "_load_user_conversations"
        ) as mock_load:
            mock_load.side_effect = Exception("Simulated general error")

            result = conversation_manager.update_conversation_title(
                test_username, conversation_id, "New Title"
            )
            assert result == False, "Should return False when general exception occurs"

    print("✓ General exception handling works correctly")


def test_concurrent_title_updates():
    """Test concurrent title updates (thread safety)."""
    print("\n🧪 Testing concurrent title updates...")

    import threading
    import time

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(
            test_username, "Original"
        )

        results = []
        errors = []

        def update_title_thread(title_suffix):
            try:
                result = conversation_manager.update_conversation_title(
                    test_username, conversation_id, f"Title {title_suffix}"
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=update_title_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        assert len(errors) == 0, (
            f"No errors should occur in concurrent execution: {errors}"
        )
        assert len(results) == 5, f"All threads should complete: {len(results)}"
        assert all(results), "All title updates should succeed"

        # Verify final conversation state is valid
        final_conversation = conversation_manager.get_conversation(
            test_username, conversation_id
        )
        assert final_conversation is not None, "Conversation should still exist"
        assert final_conversation.chat_name.startswith("Title "), (
            f"Final title should be valid: {final_conversation.chat_name}"
        )

    print("✓ Concurrent title updates work correctly")


def test_logging_functionality():
    """Test that proper logging occurs during title updates."""
    print("\n🧪 Testing logging functionality...")

    with tempfile.TemporaryDirectory() as temp_dir:
        conversation_manager = ConversationManager(temp_dir)

        # Create a test conversation
        test_username = "test_user"
        conversation_id = conversation_manager.create_conversation(
            test_username, "Original"
        )

        # Test successful update logging
        with patch("logging.info") as mock_info:
            result = conversation_manager.update_conversation_title(
                test_username, conversation_id, "New Title"
            )
            assert result == True, "Title update should succeed"
            mock_info.assert_called_once()
            assert "Updated title for conversation" in str(mock_info.call_args)

        # Test warning logging for nonexistent conversation
        with patch("logging.warning") as mock_warning:
            result = conversation_manager.update_conversation_title(
                test_username, "fake-id", "Title"
            )
            assert result == False, "Should fail for nonexistent conversation"
            mock_warning.assert_called_once()
            assert "not found" in str(mock_warning.call_args)

        # Test error logging for invalid title
        with patch("logging.warning") as mock_warning:
            result = conversation_manager.update_conversation_title(
                test_username, conversation_id, None
            )
            assert result == False, "Should fail for invalid title"
            mock_warning.assert_called_once()
            assert "Invalid title" in str(mock_warning.call_args)

    print("✓ Logging functionality works correctly")


def test_persistence_across_manager_instances():
    """Test that title updates persist across ConversationManager instances."""
    print("\n🧪 Testing persistence across manager instances...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create conversation with first manager instance
        conversation_manager1 = ConversationManager(temp_dir)
        test_username = "test_user"
        conversation_id = conversation_manager1.create_conversation(
            test_username, "Original"
        )

        # Update title
        result = conversation_manager1.update_conversation_title(
            test_username, conversation_id, "Updated Title"
        )
        assert result == True, "Title update should succeed"

        # Create new manager instance and verify persistence
        conversation_manager2 = ConversationManager(temp_dir)
        conversation = conversation_manager2.get_conversation(
            test_username, conversation_id
        )

        assert conversation is not None, "Conversation should persist"
        assert conversation.chat_name == "Updated Title", (
            f"Updated title should persist: {conversation.chat_name}"
        )

    print("✓ Persistence across manager instances works correctly")


def run_all_tests():
    """Run all ConversationManager title update tests."""
    print("🚀 Starting ConversationManager title update tests...")

    try:
        test_conversation_manager_title_update_method_exists()
        test_successful_title_update()
        test_title_sanitization()
        test_nonexistent_conversation()
        test_invalid_title_validation()
        test_storage_error_handling()
        test_general_exception_handling()
        test_concurrent_title_updates()
        test_logging_functionality()
        test_persistence_across_manager_instances()

        print("\n✅ All ConversationManager title update tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
