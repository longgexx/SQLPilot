from sqlpilot.prompts.main_agent import SYSTEM_PROMPT

def test_system_prompt_content():
    """Verify that the system prompt contains critical sections."""
    assert "Senior DBA" in SYSTEM_PROMPT
    assert "# TOOLS AVAILABLE" in SYSTEM_PROMPT
    assert "execute_and_compare" in SYSTEM_PROMPT
    assert "# OUTPUT FORMAT" in SYSTEM_PROMPT
    assert "json" in SYSTEM_PROMPT
