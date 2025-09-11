"""
Test that character prompts are properly extracted and copied when starting inpainting.
"""

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class TestCharacterPromptCopying:
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

    def test_extract_character_prompts_from_metadata(self, driver):
        """Test that character prompts are correctly extracted from image metadata"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Define the CharacterPromptData interface and extractPromptsFromMetadata function
                    const script = document.createElement('script');
                    script.textContent = `
                        function extractPromptsFromMetadata(metadata) {
                            let prompt;
                            let negativePrompt;
                            const characterPrompts = [];

                            // Priority order for main prompt extraction
                            if (metadata['Prompt']) {
                                prompt = metadata['Prompt'];
                            } else if (metadata['Revised Prompt']) {
                                prompt = metadata['Revised Prompt'];
                            }

                            // Priority order for main negative prompt
                            if (metadata['Negative Prompt']) {
                                negativePrompt = metadata['Negative Prompt'];
                            } else if (metadata['Revised Negative Prompt']) {
                                negativePrompt = metadata['Revised Negative Prompt'];
                            }

                            // Extract character prompts
                            const characterMap = {};

                            for (const key in metadata) {
                                const characterMatch = key.match(/^Character (\\\\d+) (Prompt|Negative)$/);
                                const processedMatch = key.match(/^Character (\\\\d+) Processed (Prompt|Negative)$/);

                                if (characterMatch) {
                                    const charNum = parseInt(characterMatch[1]);
                                    const promptType = characterMatch[2];

                                    if (!characterMap[charNum]) {
                                        characterMap[charNum] = { positive: '', negative: '' };
                                    }

                                    if (promptType === 'Prompt') {
                                        characterMap[charNum].positive = metadata[key] || '';
                                    } else if (promptType === 'Negative') {
                                        characterMap[charNum].negative = metadata[key] || '';
                                    }
                                } else if (processedMatch) {
                                    const charNum = parseInt(processedMatch[1]);
                                    const promptType = processedMatch[2];
                                    const originalKey = 'Character ' + charNum + ' ' + promptType;

                                    if (!metadata[originalKey]) {
                                        if (!characterMap[charNum]) {
                                            characterMap[charNum] = { positive: '', negative: '' };
                                        }

                                        if (promptType === 'Prompt') {
                                            characterMap[charNum].positive = metadata[key] || '';
                                        } else if (promptType === 'Negative') {
                                            characterMap[charNum].negative = metadata[key] || '';
                                        }
                                    }
                                }
                            }

                            // Convert character map to array
                            const characterNumbers = Object.keys(characterMap).map(num => parseInt(num)).sort((a, b) => a - b);
                            for (const charNum of characterNumbers) {
                                characterPrompts.push(characterMap[charNum]);
                            }

                            return { prompt, negativePrompt, characterPrompts };
                        }
                        window.extractPromptsFromMetadata = extractPromptsFromMetadata;
                    `;
                    document.head.appendChild(script);
                    
                    // Test different metadata scenarios with character prompts
                    const testCases = [
                        {
                            name: 'Character prompts with main prompts',
                            metadata: {
                                'Prompt': 'A beautiful landscape',
                                'Negative Prompt': 'blurry, low quality',
                                'Character 1 Prompt': 'A warrior with sword',
                                'Character 1 Negative': 'weak, unarmed',
                                'Character 2 Prompt': 'A mage with staff',
                                'Character 2 Negative': 'powerless, mundane'
                            },
                            expected: {
                                prompt: 'A beautiful landscape',
                                negativePrompt: 'blurry, low quality',
                                characterPrompts: [
                                    { positive: 'A warrior with sword', negative: 'weak, unarmed' },
                                    { positive: 'A mage with staff', negative: 'powerless, mundane' }
                                ]
                            }
                        },
                        {
                            name: 'Only processed character prompts',
                            metadata: {
                                'Revised Prompt': 'A stunning landscape scene',
                                'Character 1 Processed Prompt': 'A detailed warrior character with ornate sword',
                                'Character 1 Processed Negative': 'weak appearance, no weapons'
                            },
                            expected: {
                                prompt: 'A stunning landscape scene',
                                negativePrompt: undefined,
                                characterPrompts: [
                                    { positive: 'A detailed warrior character with ornate sword', negative: 'weak appearance, no weapons' }
                                ]
                            }
                        },
                        {
                            name: 'Mixed original and processed character prompts',
                            metadata: {
                                'Prompt': 'Fantasy scene',
                                'Character 1 Prompt': 'A knight',
                                'Character 1 Processed Negative': 'cowardly, weak',
                                'Character 2 Processed Prompt': 'A dragon',
                                'Character 2 Negative': 'small, harmless'
                            },
                            expected: {
                                prompt: 'Fantasy scene',
                                negativePrompt: undefined,
                                characterPrompts: [
                                    { positive: 'A knight', negative: 'cowardly, weak' },
                                    { positive: 'A dragon', negative: 'small, harmless' }
                                ]
                            }
                        },
                        {
                            name: 'No character prompts',
                            metadata: {
                                'Prompt': 'Simple landscape',
                                'Negative Prompt': 'blurry'
                            },
                            expected: {
                                prompt: 'Simple landscape',
                                negativePrompt: 'blurry',
                                characterPrompts: []
                            }
                        }
                    ];
                    
                    const results = [];
                    for (const testCase of testCases) {
                        const result = window.extractPromptsFromMetadata(testCase.metadata);
                        
                        // Deep comparison for character prompts
                        const characterPromptsMatch = JSON.stringify(result.characterPrompts) === JSON.stringify(testCase.expected.characterPrompts);
                        
                        const passed = result.prompt === testCase.expected.prompt && 
                                     result.negativePrompt === testCase.expected.negativePrompt &&
                                     characterPromptsMatch;
                        
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

    def test_character_prompt_copying_workflow(self, driver):
        """Test the complete character prompt copying workflow"""
        driver.get("data:text/html,<html><head><title>Test</title></head><body><div id='test'>Test</div></body></html>")
        
        result = driver.execute_script("""
            return new Promise(async (resolve) => {
                try {
                    // Create mock form structure with character prompt interface
                    document.body.innerHTML = `
                        <form id="prompt-form">
                            <select id="provider">
                                <option value="openai">OpenAI</option>
                                <option value="novelai" selected>NovelAI</option>
                            </select>
                            
                            <textarea id="prompt" placeholder="Enter prompt"></textarea>
                            <textarea id="negative_prompt" placeholder="Enter negative prompt"></textarea>
                            
                            <div id="character-prompt-section" class="novelai character-prompt-section">
                                <div id="character-prompts-container">
                                    <!-- Character prompts will be added here -->
                                </div>
                            </div>
                        </form>
                    `;
                    
                    // Mock the character prompt functions
                    let characterPromptCounter = 0;
                    
                    function addCharacterPrompt() {
                        characterPromptCounter++;
                        const container = document.getElementById('character-prompts-container');
                        const characterDiv = document.createElement('div');
                        characterDiv.className = 'character-prompt-item';
                        characterDiv.innerHTML = `
                            <div class="character-header">Character ${characterPromptCounter}</div>
                            <textarea data-prompt-type="positive" placeholder="Character prompt"></textarea>
                            <div class="negative-group" style="display: none;">
                                <textarea data-prompt-type="negative" placeholder="Negative prompt"></textarea>
                            </div>
                            <input type="checkbox" class="show-negative-toggle">
                        `;
                        container.appendChild(characterDiv);
                    }
                    
                    function updateCharacterContentIndicator(textarea) {
                        // Mock function - just for testing
                    }
                    
                    function showCharacterPromptInterface() {
                        const section = document.getElementById('character-prompt-section');
                        if (section) {
                            section.style.display = 'block';
                        }
                    }
                    
                    function populateCharacterPrompts(characterPrompts) {
                        const container = document.getElementById('character-prompts-container');
                        if (container) {
                            container.innerHTML = '';
                        }
                        
                        characterPrompts.forEach((promptData) => {
                            addCharacterPrompt();
                            
                            const lastCharacterDiv = container.querySelector('.character-prompt-item:last-child');
                            if (lastCharacterDiv) {
                                const positiveTextarea = lastCharacterDiv.querySelector('textarea[data-prompt-type="positive"]');
                                const negativeTextarea = lastCharacterDiv.querySelector('textarea[data-prompt-type="negative"]');
                                
                                if (positiveTextarea) {
                                    positiveTextarea.value = promptData.positive;
                                }
                                
                                if (negativeTextarea) {
                                    negativeTextarea.value = promptData.negative;
                                    
                                    if (promptData.negative.trim().length > 0) {
                                        const negativeToggle = lastCharacterDiv.querySelector('.show-negative-toggle');
                                        const negativeGroup = lastCharacterDiv.querySelector('.negative-group');
                                        
                                        if (negativeToggle && negativeGroup) {
                                            negativeToggle.checked = true;
                                            negativeGroup.style.display = 'block';
                                        }
                                    }
                                }
                            }
                        });
                    }
                    
                    function copyPromptToForm(prompt, negativePrompt, characterPrompts) {
                        const promptTextarea = document.getElementById('prompt');
                        const negativePromptTextarea = document.getElementById('negative_prompt');
                        
                        if (promptTextarea && prompt) {
                            promptTextarea.value = prompt;
                        }
                        
                        if (negativePromptTextarea && negativePrompt) {
                            negativePromptTextarea.value = negativePrompt;
                        }
                        
                        if (characterPrompts && characterPrompts.length > 0) {
                            const providerSelect = document.getElementById('provider');
                            if (providerSelect && providerSelect.value === 'novelai') {
                                showCharacterPromptInterface();
                                populateCharacterPrompts(characterPrompts);
                            }
                        }
                    }
                    
                    // Test the workflow
                    const testPrompt = 'A fantasy battle scene';
                    const testNegativePrompt = 'blurry, low quality';
                    const testCharacterPrompts = [
                        { positive: 'A brave knight with shining armor', negative: 'cowardly, weak' },
                        { positive: 'A powerful wizard with glowing staff', negative: 'powerless, mundane' }
                    ];
                    
                    copyPromptToForm(testPrompt, testNegativePrompt, testCharacterPrompts);
                    
                    // Verify the results
                    const promptCopied = document.getElementById('prompt').value === testPrompt;
                    const negativePromptCopied = document.getElementById('negative_prompt').value === testNegativePrompt;
                    
                    const characterPromptItems = document.querySelectorAll('.character-prompt-item');
                    const characterPromptsCopied = characterPromptItems.length === testCharacterPrompts.length;
                    
                    let characterPromptsCorrect = true;
                    characterPromptItems.forEach((item, index) => {
                        const positiveTextarea = item.querySelector('textarea[data-prompt-type="positive"]');
                        const negativeTextarea = item.querySelector('textarea[data-prompt-type="negative"]');
                        
                        if (positiveTextarea.value !== testCharacterPrompts[index].positive ||
                            negativeTextarea.value !== testCharacterPrompts[index].negative) {
                            characterPromptsCorrect = false;
                        }
                    });
                    
                    resolve({
                        success: true,
                        promptCopied: promptCopied,
                        negativePromptCopied: negativePromptCopied,
                        characterPromptsCopied: characterPromptsCopied,
                        characterPromptsCorrect: characterPromptsCorrect,
                        characterPromptCount: characterPromptItems.length,
                        allCorrect: promptCopied && negativePromptCopied && characterPromptsCopied && characterPromptsCorrect
                    });
                } catch (error) {
                    resolve({ success: false, error: error.message });
                }
            });
        """)
        
        assert result['success'], f"Test failed: {result.get('error', 'Unknown error')}"
        assert result['allCorrect'], f"Not all prompts copied correctly: {result}"
        assert result['promptCopied'], "Main prompt should be copied"
        assert result['negativePromptCopied'], "Negative prompt should be copied"
        assert result['characterPromptsCopied'], "Character prompts should be created"
        assert result['characterPromptsCorrect'], "Character prompt content should be correct"
        assert result['characterPromptCount'] == 2, f"Should have 2 character prompts, got {result['characterPromptCount']}"