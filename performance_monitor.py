#!/usr/bin/env python3
"""
Performance monitoring utility for the OpenAI API migration.
Provides logging and monitoring capabilities for API usage and system performance.
"""

import time
import logging
from functools import wraps
from typing import Any, Callable, Dict
from collections import defaultdict, deque
import threading


class PerformanceMonitor:
    """Monitor and log performance metrics for the application."""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.api_calls = deque(maxlen=1000)  # Keep last 1000 API calls
        self.conversation_ops = deque(maxlen=1000)  # Keep last 1000 conversation operations
        self._lock = threading.Lock()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('PerformanceMonitor')
    
    def time_operation(self, operation_name: str):
        """Decorator to time operations and log performance metrics."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self._record_metric(operation_name, duration, success=True)
                    
                    if duration > 1.0:  # Log slow operations
                        self.logger.warning(f"Slow operation: {operation_name} took {duration:.3f}s")
                    
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self._record_metric(operation_name, duration, success=False)
                    self.logger.error(f"Operation failed: {operation_name} after {duration:.3f}s - {e}")
                    raise
            return wrapper
        return decorator
    
    def _record_metric(self, operation_name: str, duration: float, success: bool = True):
        """Record a performance metric."""
        with self._lock:
            metric_data = {
                'timestamp': time.time(),
                'duration': duration,
                'success': success
            }
            self.metrics[operation_name].append(metric_data)
            
            # Keep only last 100 metrics per operation
            if len(self.metrics[operation_name]) > 100:
                self.metrics[operation_name] = self.metrics[operation_name][-100:]
    
    def log_api_call(self, api_type: str, duration: float, success: bool = True, error: str = None):
        """Log API call metrics."""
        with self._lock:
            call_data = {
                'timestamp': time.time(),
                'api_type': api_type,
                'duration': duration,
                'success': success,
                'error': error
            }
            self.api_calls.append(call_data)
            
            if not success:
                self.logger.error(f"API call failed: {api_type} - {error}")
            elif duration > 5.0:
                self.logger.warning(f"Slow API call: {api_type} took {duration:.3f}s")
    
    def log_conversation_operation(self, operation: str, username: str, duration: float, success: bool = True):
        """Log conversation operation metrics."""
        with self._lock:
            op_data = {
                'timestamp': time.time(),
                'operation': operation,
                'username': username,
                'duration': duration,
                'success': success
            }
            self.conversation_ops.append(op_data)
            
            if duration > 2.0:  # Log slow conversation operations
                self.logger.warning(f"Slow conversation operation: {operation} for {username} took {duration:.3f}s")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics."""
        with self._lock:
            summary = {}
            
            # API call statistics
            if self.api_calls:
                recent_calls = [call for call in self.api_calls if time.time() - call['timestamp'] < 3600]  # Last hour
                total_calls = len(recent_calls)
                successful_calls = len([call for call in recent_calls if call['success']])
                avg_duration = sum(call['duration'] for call in recent_calls) / total_calls if total_calls > 0 else 0
                
                summary['api_calls'] = {
                    'total_last_hour': total_calls,
                    'success_rate': successful_calls / total_calls if total_calls > 0 else 0,
                    'average_duration': avg_duration
                }
            
            # Conversation operation statistics
            if self.conversation_ops:
                recent_ops = [op for op in self.conversation_ops if time.time() - op['timestamp'] < 3600]  # Last hour
                total_ops = len(recent_ops)
                successful_ops = len([op for op in recent_ops if op['success']])
                avg_duration = sum(op['duration'] for op in recent_ops) / total_ops if total_ops > 0 else 0
                
                summary['conversation_ops'] = {
                    'total_last_hour': total_ops,
                    'success_rate': successful_ops / total_ops if total_ops > 0 else 0,
                    'average_duration': avg_duration
                }
            
            # Operation-specific metrics
            for operation_name, metrics in self.metrics.items():
                recent_metrics = [m for m in metrics if time.time() - m['timestamp'] < 3600]  # Last hour
                if recent_metrics:
                    total = len(recent_metrics)
                    successful = len([m for m in recent_metrics if m['success']])
                    avg_duration = sum(m['duration'] for m in recent_metrics) / total
                    
                    summary[operation_name] = {
                        'total_last_hour': total,
                        'success_rate': successful / total,
                        'average_duration': avg_duration
                    }
            
            return summary
    
    def log_system_health(self):
        """Log overall system health metrics."""
        summary = self.get_performance_summary()
        self.logger.info(f"System performance summary: {summary}")


# Global performance monitor instance
performance_monitor = PerformanceMonitor()