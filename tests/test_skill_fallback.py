"""Tests for rk skill fallback workflow.

SPEC-055: Update rk Skill to Handle Fallback Workflow
"""

from __future__ import annotations

import pytest
from pathlib import Path


class TestSkillFallbackWorkflow:
    """Test that the rk skill template correctly handles fallback scenarios."""

    def test_skill_template_includes_fallback_section(self):
        """Verify the skill template includes fallback workflow instructions."""
        from research_keeper.skill_template import SKILL_CONTENT

        assert "Fallback Workflow" in SKILL_CONTENT
        assert "JavaScript" in SKILL_CONTENT
        assert "Playwright" in SKILL_CONTENT
        assert "--content" in SKILL_CONTENT

    def test_skill_template_includes_recognition_pattern(self):
        """Verify the skill template teaches agents to recognize fetch failures."""
        from research_keeper.skill_template import SKILL_CONTENT

        # Should include error pattern recognition
        assert "Error adding" in SKILL_CONTENT
        assert "Failed to fetch URL" in SKILL_CONTENT
        assert "Hint:" in SKILL_CONTENT

    def test_skill_template_includes_fallback_steps(self):
        """Verify the skill template provides clear fallback steps."""
        from research_keeper.skill_template import SKILL_CONTENT

        # Should have numbered steps
        assert "1." in SKILL_CONTENT or "**1**" in SKILL_CONTENT
        assert "2." in SKILL_CONTENT or "**2**" in SKILL_CONTENT
        assert "Fetch" in SKILL_CONTENT or "fetch" in SKILL_CONTENT
        assert "Retry" in SKILL_CONTENT or "retry" in SKILL_CONTENT

    def test_skill_template_includes_code_example(self):
        """Verify the skill template includes Playwright example."""
        from research_keeper.skill_template import SKILL_CONTENT

        assert "playwright" in SKILL_CONTENT.lower()
        assert "sync_playwright" in SKILL_CONTENT
        assert "browser" in SKILL_CONTENT

    def test_skill_template_mentions_zero_overhead(self):
        """Verify the skill template emphasizes zero overhead for normal pages."""
        from research_keeper.skill_template import SKILL_CONTENT

        assert "Zero overhead" in SKILL_CONTENT or "zero overhead" in SKILL_CONTENT
        assert "Normal pages" in SKILL_CONTENT or "normal pages" in SKILL_CONTENT

    def test_skill_template_updates_requirements(self):
        """Verify the requirements section includes Playwright."""
        from research_keeper.skill_template import SKILL_CONTENT

        assert "Playwright" in SKILL_CONTENT or "playwright" in SKILL_CONTENT
        assert "browser" in SKILL_CONTENT.lower()


class TestSkillFallbackScenarios:
    """Test specific fallback scenarios with mock agent interactions."""

    def test_javascript_heavy_page_scenario(self):
        """Scenario 1: JavaScript-heavy page should trigger fallback."""
        # This is a conceptual test - actual agent testing requires subagent framework
        # Test verifies the scenario is documented
        scenario_file = (
            Path(__file__).parent
            / "fixtures"
            / "skill-scenarios"
            / "fallback-workflow.md"
        )

        assert scenario_file.exists()
        content = scenario_file.read_text()

        assert "Scenario 1: JavaScript-Heavy Page" in content
        assert "Playwright is available" in content
        assert "Content added successfully" in content

    def test_normal_page_zero_overhead_scenario(self):
        """Scenario 2: Normal page should not trigger fallback."""
        scenario_file = (
            Path(__file__).parent
            / "fixtures"
            / "skill-scenarios"
            / "fallback-workflow.md"
        )
        content = scenario_file.read_text()

        assert "Scenario 2: Normal Page" in content
        assert "Zero Overhead" in content
        assert "No fallback triggered" in content

    def test_total_failure_scenario(self):
        """Scenario 3: All methods fail should provide clear error."""
        scenario_file = (
            Path(__file__).parent
            / "fixtures"
            / "skill-scenarios"
            / "fallback-workflow.md"
        )
        content = scenario_file.read_text()

        assert "Scenario 3: Total Failure" in content
        assert "actionable error" in content
        assert "suggests alternatives" in content

    def test_pressure_variations_documented(self):
        """Verify pressure test variations are documented."""
        scenario_file = (
            Path(__file__).parent
            / "fixtures"
            / "skill-scenarios"
            / "fallback-workflow.md"
        )
        content = scenario_file.read_text()

        assert "Pressure Variations" in content
        assert "Time Pressure" in content
        assert "Sunk Cost Pressure" in content
        assert "Authority Pressure" in content
