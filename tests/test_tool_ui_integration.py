"""
Simple integration tests for tool configuration UI.
Tests that the HTML structure is correct and backend can handle tool data.
"""

import pytest
import re


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated client."""
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
    return client


def test_tool_configuration_html_structure(authenticated_client):
    """Test that tool configuration HTML is present in the page."""
    # Get the main page
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Check for tool configuration section (it has multiple classes)
    assert 'tool-configuration' in html, "Tool configuration section should exist"
    
    # Check for tool categories
    assert 'tool-category' in html, "Tool categories should exist"
    assert html.count('tool-category') >= 2, "Should have at least 2 tool categories"
    
    # Check for web_search checkbox
    assert 'id="tool-web_search"' in html, "Web search checkbox should exist"
    assert 'value="web_search"' in html, "Web search checkbox should have correct value"
    
    # Check for calculator checkbox
    assert 'id="tool-calculator"' in html, "Calculator checkbox should exist"
    assert 'value="calculator"' in html, "Calculator checkbox should have correct value"


def test_tool_category_titles(authenticated_client):
    """Test that tool category titles are present."""
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Check for category titles
    assert 'class="tool-category-title"' in html, "Should have category titles"
    
    # Check for "Built-in Tools" and "Custom Tools"
    assert 'Built-in Tools' in html, "Should have Built-in Tools category"
    assert 'Custom Tools' in html, "Should have Custom Tools category"


def test_tool_descriptions_present(authenticated_client):
    """Test that tool descriptions are present."""
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Check for tool descriptions
    assert 'class="tool-description"' in html, "Should have tool descriptions"
    assert html.count('class="tool-description"') >= 2, "Should have at least 2 tool descriptions"
    
    # Check for specific descriptions
    assert 'Search the internet for current information' in html, "Should have web search description"
    assert 'Evaluate mathematical expressions safely' in html, "Should have calculator description"


def test_tool_labels_present(authenticated_client):
    """Test that tool labels are properly structured."""
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Check for tool labels
    assert 'class="tool-label"' in html, "Should have tool labels"
    assert html.count('class="tool-label"') >= 2, "Should have at least 2 tool labels"
    
    # Check for tool names
    assert 'class="tool-name"' in html, "Should have tool names"
    assert 'Web Search' in html, "Should have Web Search tool name"
    assert 'Calculator' in html, "Should have Calculator tool name"


def test_tool_checkboxes_have_name_attribute(authenticated_client):
    """Test that tool checkboxes have the correct name attribute for form collection."""
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Find all tool checkboxes with name="tool" (order of attributes may vary)
    tool_checkbox_pattern = r'<input[^>]*name="tool"[^>]*>'
    tool_checkboxes = re.findall(tool_checkbox_pattern, html)
    assert len(tool_checkboxes) >= 2, f"Should have at least 2 tool checkboxes, found {len(tool_checkboxes)}"
    
    # Check that each has a value attribute
    for checkbox in tool_checkboxes:
        assert 'value=' in checkbox, "Each checkbox should have a value attribute"


def test_agent_preset_form_contains_tools(authenticated_client):
    """Test that the agent preset form contains the tool configuration section."""
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Find the agent preset form
    assert 'id="agent-preset-form"' in html, "Agent preset form should exist"
    
    # Check that tool configuration appears after the form starts
    form_start = html.find('id="agent-preset-form"')
    tool_config_pos = html.find('tool-configuration')
    form_end = html.find('</form>', form_start)
    
    assert form_start > 0, "Form should exist"
    assert tool_config_pos > 0, "Tool configuration should exist"
    assert form_start < tool_config_pos < form_end, "Tool configuration should be inside the form"


def test_tool_configuration_styling_classes(authenticated_client):
    """Test that tool configuration has proper styling classes."""
    response = authenticated_client.get('/')
    assert response.status_code == 200
    
    html = response.data.decode('utf-8')
    
    # Check for tool-option divs
    assert 'class="tool-option"' in html, "Should have tool-option divs"
    assert html.count('class="tool-option"') >= 2, "Should have at least 2 tool options"
    
    # Check that tool options contain checkboxes and labels
    assert 'type="checkbox"' in html, "Tool options should contain checkboxes"
    assert 'class="tool-label"' in html, "Tool options should contain labels"
