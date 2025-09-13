# Implementation Plan

- [x] 1. Organize inpainting source files into subfolder






  - Create `src/inpainting/` directory
  - Move inpainting-related TypeScript files to the new subfolder
  - Update all import statements in dependent files to use new paths
  - Verify TypeScript compilation succeeds after moves
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Clean up redundant reasoning API tests





  - Analyze reasoning test files to identify overlapping functionality
  - Consolidate `test_reasoning_*.py` files into core reasoning tests
  - Remove duplicate integration tests and redundant error handling tests
  - Verify remaining tests provide comprehensive coverage
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Consolidate undo/redo button tests









  - Keep `test_undo_redo_buttons.py` as the comprehensive test
  - Remove `test_undo_redo_debug.py` and `test_undo_redo_buttons_fix.py`
  - Verify remaining test covers all undo/redo functionality
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3b. Cleanup outdated tests


  - Cleanup any tests that point to test-inpainting-canvas or similar endpoints that no longer exists
  - Replace or combine tests that have equivalent logic that use the main user endpoints.

- [x] 4. Consolidate performance optimization tests






  - Merge `test_performance_optimizations.py` and `test_performance_optimizations_unit.py`
  - Create single comprehensive performance test file
  - Remove duplicate test implementations
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. Consolidate mask export tests






  - Merge `test_mask_export_functionality.py`, `test_mask_export_unit.py`, and `test_mask_export_verification.py`
  - Create single comprehensive mask export test file
  - Remove redundant test implementations
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Clean up webworker tests





  - Keep core webworker functionality tests
  - Remove redundant `test_webworker_integration.py` and `test_worker_recursion_fix.py`
  - Verify remaining tests cover essential webworker functionality
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 7. Consolidate seed functionality tests





  - Merge `test_seed_functionality.py` and `test_seed_integration.py`
  - Create single comprehensive seed test file
  - Remove duplicate test implementations
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_


- [x] 9. Cleanup redundant tests that just read the contents of ts/js files





  - Identify tests that read the contents of TypeScript/JavaScript files
  - Either remove the useless tests, or replace with something that actually tests the functionality.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 8. Consolidate misc. tests





  - Cleanup race condition, worker, zoom pan tests
  - Verify remaining tests cover essential functionality
  - Ensure all tests are passing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 10. Connect Generate Grid to unified image API








  - Identify Generate Grid functionality in frontend code
  - Update Generate Grid to use unified `/image` endpoint for batch generation
  - Remove legacy Generate Grid implementation that bypasses unified API
  - Test Generate Grid functionality with unified API
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 11. Remove legacy webworker implementations





  - Identify old implementations replaced by webworker async equivalents
  - Verify async replacements handle all use cases
  - Update any remaining references to use async implementations
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 12. Identify and remove dead code paths





  - Scan codebase for unused functions and classes
  - Identify unreachable code paths and outdated testing infrastructure
  - Verify no active functionality depends on identified dead code
  - Remove dead code and update imports accordingly
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 13. Remove commented-out code blocks





  - Search for commented-out code blocks throughout the codebase
  - Remove commented code that serves no documentation purpose
  - Preserve comments that explain complex logic or provide context
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 14. Clean up debugging console output




  - Remove `console.log()` statements used for debugging in TypeScript files
  - Remove `print()` statements used for debugging in Python files
  - Remove development-only performance timing code
  - Preserve error logging and user-facing status messages
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 15. Upgrade operational monitoring to frontend displays
  - Identify operational monitoring that currently uses print/console output
  - Replace with user-visible progress indicators or status displays in the UI
  - Remove console-based performance monitoring
  - Test that operational information is still accessible to users
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 16. Consolidate duplicate code implementations
  - Identify duplicate function implementations across the codebase
  - Identify similar code patterns that can be abstracted into utilities
  - Create reusable utility functions for common patterns
  - Update all references to use consolidated implementations
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 17. Add minimal function documentation
  - Identify functions lacking documentation in Python and TypeScript files
  - Write brief, clear docstrings focusing on function purpose and key parameters
  - Avoid verbose or redundant comments
  - Follow Python and TypeScript documentation conventions
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 18. Apply consistent code organization patterns
  - Identify inconsistent naming patterns across the codebase
  - Identify misplaced utility functions that should be grouped together
  - Reorganize code to group related functionality
  - Update references to moved code while maintaining existing import paths where possible
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 19. Verify system functionality after cleanup
  - Run full test suite to ensure no regressions
  - Test key user workflows manually
  - Verify TypeScript compilation succeeds
  - Test grid functionality and image generation workflows
  - _Requirements: All requirements verification_