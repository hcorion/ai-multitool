"""
Unit test to verify that currentThreadId is properly exposed to window object.
This test verifies the fix for the reasoning inspection button bug.
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock


class TestConversationIdWindowExposure:
    """Test that currentThreadId is properly exposed to the window object."""

    def test_typescript_compilation_includes_window_exposure(self):
        """Test that the compiled JavaScript includes window.currentThreadId assignment."""
        
        # Read the compiled JavaScript file
        js_file_path = "static/js/script.js"
        
        if not os.path.exists(js_file_path):
            pytest.skip("Compiled JavaScript file not found. Run 'tsc' to compile TypeScript.")
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that window.currentThreadId is being set
        assert 'window.currentThreadId = currentThreadId' in js_content, \
            "window.currentThreadId assignment not found in compiled JavaScript"
        
        # Check that it's set in both places where currentThreadId is assigned
        # 1. When loading existing conversations
        # 2. When starting new conversations
        
        # Count occurrences to ensure both locations are covered
        window_assignments = js_content.count('window.currentThreadId = currentThreadId')
        assert window_assignments >= 2, \
            f"Expected at least 2 window.currentThreadId assignments, found {window_assignments}"

    def test_chat_module_accesses_window_current_thread_id(self):
        """Test that the chat module correctly accesses window.currentThreadId."""
        
        # Read the compiled chat JavaScript file
        chat_js_file_path = "static/js/chat.js"
        
        if not os.path.exists(chat_js_file_path):
            pytest.skip("Compiled chat JavaScript file not found. Run 'tsc' to compile TypeScript.")
        
        with open(chat_js_file_path, 'r', encoding='utf-8') as f:
            chat_js_content = f.read()
        
        # Check that the chat module accesses window.currentThreadId
        assert 'window.currentThreadId' in chat_js_content, \
            "window.currentThreadId access not found in compiled chat JavaScript"

    def test_typescript_source_has_window_exposure_fix(self):
        """Test that the TypeScript source includes the window exposure fix."""
        
        # Read the TypeScript source file
        ts_file_path = "src/script.ts"
        
        with open(ts_file_path, 'r', encoding='utf-8') as f:
            ts_content = f.read()
        
        # Check that the fix is present in the source
        assert '(window as any).currentThreadId = currentThreadId' in ts_content, \
            "Window exposure fix not found in TypeScript source"
        
        # Check that it appears in both locations
        window_assignments = ts_content.count('(window as any).currentThreadId = currentThreadId')
        assert window_assignments >= 2, \
            f"Expected at least 2 window exposure assignments in TypeScript, found {window_assignments}"

    def test_chat_typescript_source_accesses_window(self):
        """Test that the chat TypeScript source accesses window.currentThreadId."""
        
        # Read the chat TypeScript source file
        chat_ts_file_path = "src/chat.ts"
        
        with open(chat_ts_file_path, 'r', encoding='utf-8') as f:
            chat_ts_content = f.read()
        
        # Check that the chat module accesses window.currentThreadId
        assert '(window as any).currentThreadId' in chat_ts_content, \
            "window.currentThreadId access not found in chat TypeScript source"

    def test_fix_addresses_original_bug_scenario(self):
        """Test that the fix addresses the original bug scenario."""
        
        # This test verifies the logical flow of the fix:
        # 1. When a conversation is loaded, currentThreadId is set
        # 2. currentThreadId is exposed to window
        # 3. The reasoning modal can access it via window.currentThreadId
        
        ts_file_path = "src/script.ts"
        chat_ts_file_path = "src/chat.ts"
        
        with open(ts_file_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        with open(chat_ts_file_path, 'r', encoding='utf-8') as f:
            chat_content = f.read()
        
        # Verify the fix pattern in onConversationSelected callback
        onconv_pattern = 'currentThreadId = chatData.threadId'
        window_expose_pattern = '(window as any).currentThreadId = currentThreadId'
        
        # Find the onConversationSelected callback
        onconv_start = script_content.find('chat.onConversationSelected(conversationId, (chatData: chat.MessageHistory) => {')
        assert onconv_start != -1, "onConversationSelected callback not found"
        
        # Find the end of this callback (next closing brace at same level)
        callback_section = script_content[onconv_start:onconv_start + 500]  # Look in next 500 chars
        
        # Verify both assignments are in the callback
        assert onconv_pattern in callback_section, \
            "currentThreadId assignment not found in onConversationSelected callback"
        assert window_expose_pattern in callback_section, \
            "window.currentThreadId exposure not found in onConversationSelected callback"
        
        # Verify the reasoning modal accesses window.currentThreadId
        reasoning_access_pattern = 'const conversationId = (window as any).currentThreadId'
        assert reasoning_access_pattern in chat_content, \
            "Reasoning modal doesn't access window.currentThreadId correctly"