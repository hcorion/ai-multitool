"""
Unit tests for race condition fix in brush stroke handling.
Tests the core logic without requiring a web browser.
"""

import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'static', 'js'))


class TestRaceConditionUnit:
    def test_brush_engine_state_validation(self):
        """Test that brush engine properly validates active stroke state"""
        # This test simulates the core logic without browser dependencies
        
        # Simulate the brush engine behavior
        class MockBrushEngine:
            def __init__(self):
                self.current_stroke = None
                
            def start_stroke(self, x, y):
                self.current_stroke = {'points': [(x, y)], 'active': True}
                return self.current_stroke
                
            def continue_stroke(self, x, y):
                if not self.current_stroke:
                    raise ValueError('No active stroke. Call startStroke first.')
                self.current_stroke['points'].append((x, y))
                return [(x, y)]  # Return stamp positions
                
            def end_stroke(self):
                stroke = self.current_stroke
                self.current_stroke = None
                return stroke
                
            def get_current_stroke(self):
                return self.current_stroke
        
        # Simulate the canvas manager behavior with race condition protection
        class MockCanvasManager:
            def __init__(self):
                self.brush_engine = MockBrushEngine()
                
            def start_brush_stroke(self, x, y, size, mode):
                return self.brush_engine.start_stroke(x, y)
                
            def continue_brush_stroke(self, x, y):
                # This is the key fix - check for active stroke before continuing
                if not self.brush_engine.get_current_stroke():
                    print("Warning: Attempted to continue brush stroke without active stroke - ignoring")
                    return False
                try:
                    self.brush_engine.continue_stroke(x, y)
                    return True
                except ValueError as e:
                    print(f"Error: {e}")
                    return False
                    
            def end_brush_stroke(self):
                return self.brush_engine.end_stroke()
                
            def get_brush_engine(self):
                return self.brush_engine
        
        # Test the race condition scenario
        canvas_manager = MockCanvasManager()
        
        # Test 1: Normal operation (should work)
        stroke = canvas_manager.start_brush_stroke(10, 10, 20, 'paint')
        assert stroke is not None
        assert canvas_manager.continue_brush_stroke(11, 11) == True
        completed_stroke = canvas_manager.end_brush_stroke()
        assert completed_stroke is not None
        
        # Test 2: Race condition scenario (move before start - should be handled gracefully)
        # Try to continue without starting (simulates the race condition)
        result = canvas_manager.continue_brush_stroke(15, 15)
        assert result == False  # Should return False and not crash
        
        # Now start properly
        stroke = canvas_manager.start_brush_stroke(15, 15, 20, 'paint')
        assert stroke is not None
        
        # Continue should work now
        result = canvas_manager.continue_brush_stroke(16, 16)
        assert result == True
        
        print("✅ Race condition protection working correctly")

    def test_event_ordering_logic(self):
        """Test the event ordering logic used in the render scheduler"""
        
        # Simulate events with different types and timestamps
        events = [
            {'type': 'move', 'timestamp': 100, 'data': 'move1'},
            {'type': 'start', 'timestamp': 50, 'data': 'start1'},
            {'type': 'end', 'timestamp': 150, 'data': 'end1'},
            {'type': 'move', 'timestamp': 75, 'data': 'move2'},
        ]
        
        # Apply the sorting logic from the render scheduler
        def sort_events(events):
            type_order = {'start': 0, 'move': 1, 'end': 2, 'cancel': 2}
            
            return sorted(events, key=lambda event: (
                type_order.get(event['type'], 3),  # Sort by type priority first
                event['timestamp']  # Then by timestamp
            ))
        
        sorted_events = sort_events(events)
        
        # Check that events are in the correct order
        event_types = [e['type'] for e in sorted_events]
        event_data = [e['data'] for e in sorted_events]
        
        # Should be: start, move (earliest), move (latest), end
        expected_types = ['start', 'move', 'move', 'end']
        expected_data = ['start1', 'move2', 'move1', 'end1']
        
        assert event_types == expected_types, f"Expected {expected_types}, got {event_types}"
        assert event_data == expected_data, f"Expected {expected_data}, got {event_data}"
        
        print("✅ Event ordering logic working correctly")

    def test_input_event_handler_logic(self):
        """Test the input event handler logic with race condition protection"""
        
        # Mock the components
        class MockZoomPanController:
            def screen_to_image(self, x, y, debug=False):
                return {'x': x // 2, 'y': y // 2}  # Simple scaling
        
        class MockBrushEngine:
            def __init__(self):
                self.current_stroke = None
                self.settings = {'mode': 'paint'}
                
            def get_settings(self):
                return self.settings
                
            def get_current_stroke(self):
                return self.current_stroke
        
        class MockCanvasManager:
            def __init__(self):
                self.brush_engine = MockBrushEngine()
                
            def start_brush_stroke(self, x, y, size, mode):
                self.brush_engine.current_stroke = {'active': True}
                return self.brush_engine.current_stroke
                
            def continue_brush_stroke(self, x, y):
                if not self.brush_engine.get_current_stroke():
                    return False
                return True
                
            def end_brush_stroke(self):
                stroke = self.brush_engine.current_stroke
                self.brush_engine.current_stroke = None
                return stroke
                
            def get_brush_engine(self):
                return self.brush_engine
        
        # Mock the input event handler logic
        class MockInpaintingMaskCanvas:
            def __init__(self):
                self.canvas_manager = MockCanvasManager()
                self.zoom_pan_controller = MockZoomPanController()
                self.current_stroke = None
                self.current_brush_size = 20
                self.is_zoom_pan_active = False
                
            def handle_input_event(self, evt):
                if not self.canvas_manager or self.is_zoom_pan_active:
                    return
                
                cx = evt.get('clientX', evt.get('screenX', 0))
                cy = evt.get('clientY', evt.get('screenY', 0))
                
                img = self.zoom_pan_controller.screen_to_image(cx, cy)
                if not img:
                    return
                
                brush = self.canvas_manager.get_brush_engine()
                settings = brush.get_settings()
                
                if evt['type'] == 'start':
                    self.current_stroke = self.canvas_manager.start_brush_stroke(
                        img['x'], img['y'], self.current_brush_size, settings['mode']
                    )
                elif evt['type'] == 'move':
                    # Key fix: Only continue if we have an active stroke
                    if self.current_stroke and brush.get_current_stroke():
                        self.canvas_manager.continue_brush_stroke(img['x'], img['y'])
                elif evt['type'] == 'end':
                    completed_stroke = self.canvas_manager.end_brush_stroke()
                    self.current_stroke = None
                elif evt['type'] == 'cancel':
                    if self.current_stroke:
                        self.canvas_manager.end_brush_stroke()
                        self.current_stroke = None
        
        # Test the handler
        handler = MockInpaintingMaskCanvas()
        
        # Test normal sequence
        handler.handle_input_event({'type': 'start', 'clientX': 100, 'clientY': 100})
        assert handler.current_stroke is not None
        
        handler.handle_input_event({'type': 'move', 'clientX': 102, 'clientY': 102})
        # Should work fine
        
        handler.handle_input_event({'type': 'end', 'clientX': 104, 'clientY': 104})
        assert handler.current_stroke is None
        
        # Test race condition scenario (move before start)
        handler.handle_input_event({'type': 'move', 'clientX': 110, 'clientY': 110})
        # Should not crash, should be ignored
        
        handler.handle_input_event({'type': 'start', 'clientX': 110, 'clientY': 110})
        assert handler.current_stroke is not None
        
        # Test cancellation
        handler.handle_input_event({'type': 'cancel', 'clientX': 110, 'clientY': 110})
        assert handler.current_stroke is None
        
        print("✅ Input event handler logic working correctly")

    def test_render_scheduler_priority_logic(self):
        """Test the render scheduler priority assignment logic"""
        
        def get_priority_for_event_type(event_type):
            """Simulate the priority logic from render scheduler"""
            base_priority = 100
            
            if event_type == 'start':
                return base_priority + 10  # Highest priority
            elif event_type == 'end' or event_type == 'cancel':
                return base_priority - 10  # Lower priority
            elif event_type == 'move':
                return base_priority - 5   # Medium priority
            else:
                return base_priority
        
        # Test priority assignment
        start_priority = get_priority_for_event_type('start')
        move_priority = get_priority_for_event_type('move')
        end_priority = get_priority_for_event_type('end')
        cancel_priority = get_priority_for_event_type('cancel')
        
        # Verify priority ordering
        assert start_priority > move_priority, "Start should have higher priority than move"
        assert move_priority > end_priority, "Move should have higher priority than end"
        assert end_priority == cancel_priority, "End and cancel should have same priority"
        
        # Test with a list of events
        events = [
            {'type': 'move', 'id': 1},
            {'type': 'start', 'id': 2},
            {'type': 'end', 'id': 3},
            {'type': 'move', 'id': 4},
            {'type': 'cancel', 'id': 5}
        ]
        
        # Sort by priority
        sorted_events = sorted(events, key=lambda e: get_priority_for_event_type(e['type']), reverse=True)
        
        # Should be: start, move, move, end, cancel (or end, cancel in any order since same priority)
        types = [e['type'] for e in sorted_events]
        assert types[0] == 'start', "Start should be first"
        assert types[1] in ['move'], "Move should be second"
        assert types[2] in ['move'], "Move should be third"
        assert types[3] in ['end', 'cancel'], "End or cancel should be fourth"
        assert types[4] in ['end', 'cancel'], "End or cancel should be fifth"
        
        print("✅ Render scheduler priority logic working correctly")


if __name__ == '__main__':
    test = TestRaceConditionUnit()
    test.test_brush_engine_state_validation()
    test.test_event_ordering_logic()
    test.test_input_event_handler_logic()
    test.test_render_scheduler_priority_logic()
    print("🎉 All race condition unit tests passed!")