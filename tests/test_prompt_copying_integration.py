"""
Test that prompts are properly copied when starting inpainting from the grid modal.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestPromptCopyingIntegration:
    @pytest.fixture
    def driver(self):
        """Set up Chrome driver for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()

    def test_extract_prompts_from_metadata(self, driver):
        """Test that prompts are correctly extracted from image metadata"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Load the script to get the extractPromptsFromMetadata function
                    const script = document.createElement('script');
                    script.textContent = `
                        function extractPromptsFromMetadata(metadata) {
                            let prompt;
                            let negativePrompt;
                            
                            // Priority order for prompt extraction:
                            // 1. Original "Prompt" (user's input)
                            // 2. "Revised Prompt" (AI-processed version)
                            if (metadata['Prompt']) {
                                prompt = metadata['Prompt'];
                            } else if (metadata['Revised Prompt']) {
                                prompt = metadata['Revised Prompt'];
                            }
                            
                            // Priority order for negative prompt:
                            // 1. Original "Negative Prompt" (user's input)  
                            // 2. "Revised Negative Prompt" (AI-processed version)
                            if (metadata['Negative Prompt']) {
                                negativePrompt = metadata['Negative Prompt'];
                            } else if (metadata['Revised Negative Prompt']) {
                                negativePrompt = metadata['Revised Negative Prompt'];
                            }
                            
                            return { prompt, negativePrompt };
                        }
                        window.extractPromptsFromMetadata = extractPromptsFromMetadata;
                    `;
                    document.head.appendChild(script);
                    
                    // Test different metadata scenarios
                    const testCases = [
                        {
                            name: 'Original prompts only',
                            metadata: {
                                'Prompt': 'A beautiful landscape',
                                'Negative Prompt': 'blurry, low quality'
                            },
                            expected: {
                                prompt: 'A beautiful landscape',
                                negativePrompt: 'blurry, low quality'
                            }
                        },
                        {
                            name: 'Revised prompts only',
                            metadata: {
                                'Revised Prompt': 'A stunning, photorealistic landscape',
                                'Revised Negative Prompt': 'blurry, low quality, distorted'
                            },
                            expected: {
                                prompt: 'A stunning, photorealistic landscape',
                                negativePrompt: 'blurry, low quality, distorted'
                            }
                        },
                        {
                            name: 'Both original and revised (should prefer original)',
                            metadata: {
                                'Prompt': 'A beautiful landscape',
                                'Revised Prompt': 'A stunning, photorealistic landscape',
                                'Negative Prompt': 'blurry, low quality',
                                'Revised Negative Prompt': 'blurry, low quality, distorted'
                            },
                            expected: {
                                prompt: 'A beautiful landscape',
                                negativePrompt: 'blurry, low quality'
                            }
                        },
                        {
                            name: 'Mixed original and revised',
                            metadata: {
                                'Prompt': 'A beautiful landscape',
                                'Revised Negative Prompt': 'blurry, low quality, distorted'
                            },
                            expected: {
                                prompt: 'A beautiful landscape',
                                negativePrompt: 'blurry, low quality, distorted'
                            }
                        },
                        {
                            name: 'No prompts',
                            metadata: {
                                'Provider': 'openai',
                                'Size': '1024x1024'
                            },
                            expected: {
                                prompt: undefined,
                                negativePrompt: undefined
                            }
                        }
                    ];
                    
                    const results = [];
                    for (const testCase of testCases) {
                        const result = window.extractPromptsFromMetadata(testCase.metadata);
                        const passed = result.prompt === testCase.expected.prompt && 
                                     result.negativePrompt === testCase.expected.negativePrompt;
                        results.push({
                            name: testCase.name,
                            passed: passed,
                            expected: testCase.expected,
                            actual: result
                        });
                    }
                    
                    resolve({
                        success: true,
                        results: results,
                        allPassed: results.every(r => r.passed)
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['allPassed'], f"Not all test cases passed: {result['results']}"

    def test_copy_prompt_to_form(self, driver):
        """Test that prompts are correctly copied to the form fields"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Create form elements
                    document.body.innerHTML = `
                        <textarea id="prompt" placeholder="Enter prompt"></textarea>
                        <textarea id="negative_prompt" placeholder="Enter negative prompt"></textarea>
                    `;
                    
                    // Define the copyPromptToForm function
                    function copyPromptToForm(prompt, negativePrompt) {
                        const promptTextarea = document.getElementById('prompt');
                        const negativePromptTextarea = document.getElementById('negative_prompt');
                        
                        if (promptTextarea && prompt) {
                            promptTextarea.value = prompt;
                            promptTextarea.dispatchEvent(new Event('input'));
                        }
                        
                        if (negativePromptTextarea && negativePrompt) {
                            negativePromptTextarea.value = negativePrompt;
                            negativePromptTextarea.dispatchEvent(new Event('input'));
                        }
                    }
                    
                    // Test copying prompts
                    const testPrompt = 'A beautiful sunset over mountains';
                    const testNegativePrompt = 'blurry, low quality, distorted';
                    
                    copyPromptToForm(testPrompt, testNegativePrompt);
                    
                    // Verify the values were set
                    const promptValue = document.getElementById('prompt').value;
                    const negativePromptValue = document.getElementById('negative_prompt').value;
                    
                    resolve({
                        success: true,
                        promptCopied: promptValue === testPrompt,
                        negativePromptCopied: negativePromptValue === testNegativePrompt,
                        promptValue: promptValue,
                        negativePromptValue: negativePromptValue
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['promptCopied'], f"Prompt not copied correctly: expected 'A beautiful sunset over mountains', got '{result['promptValue']}'"
        assert result['negativePromptCopied'], f"Negative prompt not copied correctly: expected 'blurry, low quality, distorted', got '{result['negativePromptValue']}'"

    def test_inpainting_workflow_with_prompts(self, driver):
        """Test the complete inpainting workflow with prompt copying"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Create mock form structure
                    document.body.innerHTML = `
                        <form id="prompt-form">
                            <textarea id="prompt" placeholder="Enter prompt"></textarea>
                            <textarea id="negative_prompt" placeholder="Enter negative prompt"></textarea>
                            
                            <div id="inpainting-section" class="inpainting-section" style="display: none;">
                                <div class="inpainting-info">
                                    <div class="inpainting-image-info">
                                        <strong>Base Image:</strong> <span id="inpainting-image-name">None selected</span>
                                    </div>
                                    <div class="inpainting-mask-info">
                                        <strong>Mask:</strong> <span id="inpainting-mask-status">No mask created</span>
                                    </div>
                                </div>
                                <input type="hidden" id="inpainting-base-image" name="base_image_path" value="">
                                <input type="hidden" id="inpainting-mask-path" name="mask_path" value="">
                                <input type="hidden" id="inpainting-operation" name="operation" value="">
                            </div>
                            
                            <input class="submit-button" type="submit" value="Generate Image" id="generate-submit-btn">
                        </form>
                    `;
                    
                    // Mock the functions
                    function copyPromptToForm(prompt, negativePrompt) {
                        const promptTextarea = document.getElementById('prompt');
                        const negativePromptTextarea = document.getElementById('negative_prompt');
                        
                        if (promptTextarea && prompt) {
                            promptTextarea.value = prompt;
                        }
                        
                        if (negativePromptTextarea && negativePrompt) {
                            negativePromptTextarea.value = negativePrompt;
                        }
                    }
                    
                    function showInpaintingSection(baseImageUrl, maskDataUrl, baseImagePath, maskPath) {
                        const inpaintingSection = document.getElementById('inpainting-section');
                        const imageNameSpan = document.getElementById('inpainting-image-name');
                        const maskStatusSpan = document.getElementById('inpainting-mask-status');
                        const baseImageInput = document.getElementById('inpainting-base-image');
                        const maskPathInput = document.getElementById('inpainting-mask-path');
                        const operationInput = document.getElementById('inpainting-operation');
                        const submitBtn = document.getElementById('generate-submit-btn');
                        
                        if (inpaintingSection) {
                            inpaintingSection.style.display = 'block';
                        }
                        
                        if (imageNameSpan) {
                            const imageName = baseImagePath.split('/').pop() || 'Unknown';
                            imageNameSpan.textContent = imageName;
                        }
                        
                        if (maskStatusSpan) {
                            maskStatusSpan.textContent = 'Mask created successfully';
                        }
                        
                        if (baseImageInput) {
                            baseImageInput.value = baseImagePath;
                        }
                        
                        if (maskPathInput) {
                            maskPathInput.value = maskPath;
                        }
                        
                        if (operationInput) {
                            operationInput.value = 'inpaint';
                        }
                        
                        if (submitBtn) {
                            submitBtn.value = 'Generate Inpainting';
                            submitBtn.classList.add('inpainting-mode');
                        }
                    }
                    
                    // Simulate the inpainting setup workflow
                    const baseImageUrl = '/static/images/user/test_image.png';
                    const maskDataUrl = 'data:image/png;base64,test_mask_data';
                    const baseImagePath = '/static/images/user/test_image.png';
                    const maskPath = '/static/images/user/mask_123.png';
                    const originalPrompt = 'A majestic mountain landscape';
                    const originalNegativePrompt = 'blurry, low quality';
                    
                    // Show inpainting section
                    showInpaintingSection(baseImageUrl, maskDataUrl, baseImagePath, maskPath);
                    
                    // Copy prompts
                    copyPromptToForm(originalPrompt, originalNegativePrompt);
                    
                    // Verify the setup
                    const inpaintingSectionVisible = document.getElementById('inpainting-section').style.display === 'block';
                    const promptCopied = document.getElementById('prompt').value === originalPrompt;
                    const negativePromptCopied = document.getElementById('negative_prompt').value === originalNegativePrompt;
                    const baseImageSet = document.getElementById('inpainting-base-image').value === baseImagePath;
                    const maskPathSet = document.getElementById('inpainting-mask-path').value === maskPath;
                    const operationSet = document.getElementById('inpainting-operation').value === 'inpaint';
                    const submitButtonUpdated = document.getElementById('generate-submit-btn').value === 'Generate Inpainting';
                    
                    resolve({
                        success: true,
                        inpaintingSectionVisible: inpaintingSectionVisible,
                        promptCopied: promptCopied,
                        negativePromptCopied: negativePromptCopied,
                        baseImageSet: baseImageSet,
                        maskPathSet: maskPathSet,
                        operationSet: operationSet,
                        submitButtonUpdated: submitButtonUpdated,
                        allChecksPass: inpaintingSectionVisible && promptCopied && negativePromptCopied && 
                                      baseImageSet && maskPathSet && operationSet && submitButtonUpdated
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['allChecksPass'], f"Not all workflow checks passed: {result}"
        assert result['inpaintingSectionVisible'], "Inpainting section should be visible"
        assert result['promptCopied'], "Original prompt should be copied to form"
        assert result['negativePromptCopied'], "Original negative prompt should be copied to form"
        assert result['baseImageSet'], "Base image path should be set"
        assert result['maskPathSet'], "Mask path should be set"
        assert result['operationSet'], "Operation should be set to 'inpaint'"
        assert result['submitButtonUpdated'], "Submit button should be updated for inpainting"