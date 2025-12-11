# Implementation Plan

- [x] 1. Create vibe data models and storage infrastructure





  - Create Pydantic models for VibeEncoding and VibeCollection with validation
  - Implement VibeStorageManager class extending UserFileManager for JSON persistence
  - Set up vibe directory structure in static/vibes/{username}/{guid}/
  - _Requirements: 1.4, 1.5, 6.1_

- [x] 1.1 Write property test for vibe storage completeness


  - **Property 2: Stored vibe completeness**
  - **Validates: Requirements 1.4, 1.5, 6.1**


- [x] 1.2 Write property test for GUID uniqueness

  - **Property 3: GUID uniqueness**
  - **Validates: Requirements 1.5**

- [x] 2. Extend NovelAI client with vibe encoding support





  - Add encode_vibe method to NovelAIClient calling https://image.novelai.net/ai/encode-vibe
  - Extend generate_image method to accept vibe references and add reference_strength_multiple/reference_image_multiple parameters
  - Create VibeReference Pydantic model for generation parameters
  - _Requirements: 1.3, 3.4, 3.5_

- [x] 2.1 Write property test for encoding strength coverage


  - **Property 1: Encoding strength coverage**
  - **Validates: Requirements 1.3**

- [x] 2.2 Write property test for vibe parameter structure


  - **Property 9: Vibe parameter structure**
  - **Validates: Requirements 3.4, 3.5**

- [x] 3. Implement vibe encoding service





  - Create VibeEncoderService class to orchestrate encoding at all 5 strength levels
  - Implement encode_vibe method that calls NovelAI API 5 times with strengths [1.0, 0.85, 0.7, 0.5, 0.35]
  - Add progress callback support for encoding phase (5 steps)
  - Handle API errors and validate responses
  - _Requirements: 1.3, 1.4_

- [x] 4. Integrate vibes with NovelAI image generation





  - Modify NovelAI client generate_image method to accept vibe references
  - Add vibe encodings and reference strengths to generation parameters
  - Pass reference_strength_multiple and reference_image_multiple arrays to NovelAI API
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Create vibe preview generation system





  - Implement VibePreviewGenerator class with fixed seed (42) and prompt ("1girl, portrait, simple background")
  - Generate 25 preview images (5 encoding × 5 reference strengths) at 512x768 resolution
  - Add progress callback support for preview generation phase (25 steps)
  - Create JPG thumbnails for each preview image
  - Store preview image paths in VibeCollection.preview_images dict
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 5.1 Write property test for preview image dimensions


  - **Property 4: Preview image dimensions**
  - **Validates: Requirements 2.4**

- [x] 5.2 Write property test for preview file completeness


  - **Property 5: Preview file completeness**
  - **Validates: Requirements 2.5, 2.6**

- [ ] 6. Implement vibe encoding API endpoints
  - Add POST /vibes/encode endpoint for creating vibe collections from existing images with progress streaming
  - Add GET /vibes endpoint for listing user's vibe collections
  - Add GET /vibes/<guid> endpoint for vibe collection details
  - Add DELETE /vibes/<guid> endpoint for vibe collection deletion
  - Add GET /vibes/<guid>/preview/<enc_strength>/<ref_strength> endpoint for preview images
  - Add Server-Sent Events (SSE) endpoint for real-time progress updates during vibe creation
  - _Requirements: 1.1, 1.2, 7.1, 7.3_

- [ ] 6.1 Write unit tests for vibe API endpoints
  - Test vibe creation flow with mocked NovelAI API
  - Test vibe listing and retrieval
  - Test vibe deletion with file cleanup verification
  - _Requirements: 1.1, 1.2, 7.3_

- [ ] 7. Create frontend vibe selection modal component
  - Implement VibeSelectionModal TypeScript class in src/vibe-modal.ts
  - Create modal HTML template with grid layout for vibe collections
  - Add discrete sliders for encoding strength (5 values) and continuous slider for reference strength (0.0-1.0)
  - Implement preview thumbnail updates based on slider values
  - Add vibe validation and compatibility checking (model compatibility, vibe count 1-4, encoding strength validation, reference strength range 0.0-1.0)
  - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 6.2, 6.3_

- [ ] 7.1 Write property test for vibe count constraint
  - **Property 6: Vibe count constraint**
  - **Validates: Requirements 3.1**

- [ ] 7.2 Write property test for encoding strength validation
  - **Property 7: Encoding strength validation**
  - **Validates: Requirements 3.2**

- [ ] 7.3 Write property test for reference strength range
  - **Property 8: Reference strength range**
  - **Validates: Requirements 3.3**

- [ ] 7.4 Write property test for model compatibility validation
  - **Property 11: Model compatibility validation**
  - **Validates: Requirements 6.2**

- [ ] 7.5 Write property test for closest reference strength selection
  - **Property 10: Closest reference strength selection**
  - **Validates: Requirements 4.5**

- [ ] 8. Implement vibe panel in generation form
  - Create VibePanel TypeScript class in src/vibe-panel.ts
  - Add "Add Vibe" button to NovelAI generation panel
  - Display selected vibes with name, thumbnail, and strength controls
  - Add remove buttons for individual vibes
  - Update form submission to include vibe parameters
  - _Requirements: 4.6, 4.7, 8.1, 8.2, 8.3_

- [ ] 9. Add grid modal vibe generation button
  - Add "Generate Vibe" button to grid modal alongside existing action buttons
  - Implement confirmation popup warning about high Anlas cost
  - Add name input dialog for vibe collection
  - Create progress modal with progress bar showing encoding (5 steps) and preview generation (25 steps) phases
  - Display live preview thumbnails as each preview image is generated
  - Integrate with vibe encoding service with progress callbacks
  - _Requirements: 1.1, 1.2_

- [ ] 10. Add copy seed functionality to grid modal
  - Add "Copy Seed" button to grid modal action buttons
  - Extract seed from image metadata and copy to generation form seed field
  - Switch to generation tab after copying seed
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 11. Add vibe management UI features
  - Display vibe collection names and creation dates in selection modal
  - Add delete confirmation dialog for vibe collections
  - Implement vibe collection deletion with file cleanup
  - _Requirements: 7.1, 7.2, 7.3_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Add error handling and user feedback
  - Implement loading spinners for vibe encoding (long operation)
  - Add toast notifications for API errors
  - Display model compatibility warnings
  - Handle NovelAI API failures gracefully
  - _Requirements: 6.3_

- [ ] 13.1 Write integration tests for complete vibe workflow
  - Test full vibe creation flow from image to preview generation
  - Test vibe usage in image generation end-to-end
  - Test error scenarios and recovery
  - _Requirements: All requirements_

- [ ] 14. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.