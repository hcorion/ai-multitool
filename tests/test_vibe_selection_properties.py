"""
Property-based tests for vibe selection modal functionality.

This module contains property-based tests to validate the correctness of
vibe selection logic, validation, and constraints.
"""

from typing import List

import pytest
from hypothesis import given, strategies as st

from vibe_models import VibeReference


class VibeSelectionValidator:
    """
    Validator class for vibe selection logic.
    
    This class implements the business logic that would be used by the frontend
    vibe selection modal to validate user selections.
    """
    
    VALID_ENCODING_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35]
    VALID_REFERENCE_STRENGTHS = [1.0, 0.85, 0.7, 0.5, 0.35]
    MIN_VIBES = 1
    MAX_VIBES = 4
    
    @classmethod
    def validate_vibe_count(cls, vibes: List[VibeReference]) -> bool:
        """Validate that vibe count is within allowed range (1-4)."""
        return cls.MIN_VIBES <= len(vibes) <= cls.MAX_VIBES
    
    @classmethod
    def validate_encoding_strength(cls, encoding_strength: float) -> bool:
        """Validate that encoding strength is one of the allowed values."""
        return encoding_strength in cls.VALID_ENCODING_STRENGTHS
    
    @classmethod
    def validate_reference_strength_range(cls, reference_strength: float) -> bool:
        """Validate that reference strength is in range [0.0, 1.0]."""
        return 0.0 <= reference_strength <= 1.0
    
    @classmethod
    def validate_model_compatibility(cls, vibe_model: str, current_model: str) -> bool:
        """Validate that vibe model is compatible with current generation model."""
        return vibe_model == current_model
    
    @classmethod
    def find_closest_reference_strength(cls, target_strength: float) -> float:
        """Find the closest pre-generated reference strength for preview display."""
        if not (0.0 <= target_strength <= 1.0):
            raise ValueError("Target strength must be in range [0.0, 1.0]")
        
        # Find the closest value from the valid reference strengths
        closest = min(cls.VALID_REFERENCE_STRENGTHS, key=lambda x: abs(x - target_strength))
        return closest


# Test data generators
@st.composite
def vibe_reference_data(draw):
    """Generate valid VibeReference data."""
    encoded_data = draw(st.text(min_size=1, max_size=1000))
    reference_strength = draw(st.floats(min_value=0.0, max_value=1.0))
    return VibeReference(encoded_data=encoded_data, reference_strength=reference_strength)


@st.composite
def vibe_list_data(draw, min_size=0, max_size=10):
    """Generate lists of VibeReference objects."""
    return draw(st.lists(vibe_reference_data(), min_size=min_size, max_size=max_size))


class TestVibeSelectionProperties:
    """Property-based tests for vibe selection validation."""
    
    @given(vibe_list_data(min_size=1, max_size=4))
    def test_vibe_count_constraint_valid(self, vibes):
        """
        **Feature: novelai-vibe-encoding, Property 6: Vibe count constraint**
        
        For any image generation request with vibes, the number of vibes should be 
        between 1 and 4 inclusive.
        
        **Validates: Requirements 3.1**
        """
        # Valid vibe counts (1-4) should pass validation
        assert VibeSelectionValidator.validate_vibe_count(vibes) is True
    
    @given(vibe_list_data(min_size=5, max_size=20))
    def test_vibe_count_constraint_too_many(self, vibes):
        """
        **Feature: novelai-vibe-encoding, Property 6: Vibe count constraint**
        
        For any image generation request with more than 4 vibes, validation should fail.
        
        **Validates: Requirements 3.1**
        """
        # Too many vibes (>4) should fail validation
        assert VibeSelectionValidator.validate_vibe_count(vibes) is False
    
    def test_vibe_count_constraint_empty(self):
        """
        **Feature: novelai-vibe-encoding, Property 6: Vibe count constraint**
        
        For any image generation request with no vibes, validation should fail.
        
        **Validates: Requirements 3.1**
        """
        # Empty vibe list should fail validation
        assert VibeSelectionValidator.validate_vibe_count([]) is False
    
    @given(st.sampled_from([1.0, 0.85, 0.7, 0.5, 0.35]))
    def test_encoding_strength_validation_valid(self, encoding_strength):
        """
        **Feature: novelai-vibe-encoding, Property 7: Encoding strength validation**
        
        For any vibe selection, the encoding strength should be one of the valid values: 
        1.0, 0.85, 0.7, 0.5, or 0.35.
        
        **Validates: Requirements 3.2**
        """
        # Valid encoding strengths should pass validation
        assert VibeSelectionValidator.validate_encoding_strength(encoding_strength) is True
    
    @given(st.floats(min_value=-10.0, max_value=10.0).filter(
        lambda x: x not in [1.0, 0.85, 0.7, 0.5, 0.35]
    ))
    def test_encoding_strength_validation_invalid(self, encoding_strength):
        """
        **Feature: novelai-vibe-encoding, Property 7: Encoding strength validation**
        
        For any vibe selection with invalid encoding strength, validation should fail.
        
        **Validates: Requirements 3.2**
        """
        # Invalid encoding strengths should fail validation
        assert VibeSelectionValidator.validate_encoding_strength(encoding_strength) is False
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_reference_strength_range_valid(self, reference_strength):
        """
        **Feature: novelai-vibe-encoding, Property 8: Reference strength range**
        
        For any vibe selection, the reference strength should be a float value 
        in the range [0.0, 1.0].
        
        **Validates: Requirements 3.3**
        """
        # Valid reference strengths (0.0-1.0) should pass validation
        assert VibeSelectionValidator.validate_reference_strength_range(reference_strength) is True
    
    @given(st.one_of(
        st.floats(min_value=-10.0, max_value=-0.001),
        st.floats(min_value=1.001, max_value=10.0)
    ))
    def test_reference_strength_range_invalid(self, reference_strength):
        """
        **Feature: novelai-vibe-encoding, Property 8: Reference strength range**
        
        For any vibe selection with reference strength outside [0.0, 1.0], 
        validation should fail.
        
        **Validates: Requirements 3.3**
        """
        # Invalid reference strengths should fail validation
        assert VibeSelectionValidator.validate_reference_strength_range(reference_strength) is False
    
    @given(st.text(min_size=1, max_size=100))
    def test_model_compatibility_validation_same(self, model_name):
        """
        **Feature: novelai-vibe-encoding, Property 11: Model compatibility validation**
        
        For any vibe used in generation, the vibe's model should match the current 
        generation model.
        
        **Validates: Requirements 6.2**
        """
        # Same model names should be compatible
        assert VibeSelectionValidator.validate_model_compatibility(model_name, model_name) is True
    
    @given(st.text(min_size=1, max_size=100), st.text(min_size=1, max_size=100))
    def test_model_compatibility_validation_different(self, vibe_model, current_model):
        """
        **Feature: novelai-vibe-encoding, Property 11: Model compatibility validation**
        
        For any vibe with different model than current generation model, 
        validation should fail.
        
        **Validates: Requirements 6.2**
        """
        # Assume different models (filter out same models)
        if vibe_model != current_model:
            assert VibeSelectionValidator.validate_model_compatibility(vibe_model, current_model) is False
    
    @given(st.floats(min_value=0.0, max_value=1.0))
    def test_closest_reference_strength_selection(self, target_strength):
        """
        **Feature: novelai-vibe-encoding, Property 10: Closest reference strength selection**
        
        For any reference strength value, the preview thumbnail should display the image 
        with the closest pre-generated reference strength value from [1.0, 0.85, 0.7, 0.5, 0.35].
        
        **Validates: Requirements 4.5**
        """
        # Find closest reference strength
        closest = VibeSelectionValidator.find_closest_reference_strength(target_strength)
        
        # Verify the result is one of the valid values
        assert closest in VibeSelectionValidator.VALID_REFERENCE_STRENGTHS
        
        # Verify it's actually the closest
        distances = [abs(target_strength - valid) for valid in VibeSelectionValidator.VALID_REFERENCE_STRENGTHS]
        min_distance = min(distances)
        assert abs(target_strength - closest) == min_distance
    
    @given(st.one_of(
        st.floats(min_value=-10.0, max_value=-0.001),
        st.floats(min_value=1.001, max_value=10.0)
    ))
    def test_closest_reference_strength_selection_invalid_range(self, target_strength):
        """
        **Feature: novelai-vibe-encoding, Property 10: Closest reference strength selection**
        
        For any reference strength value outside [0.0, 1.0], an error should be raised.
        
        **Validates: Requirements 4.5**
        """
        # Invalid target strengths should raise ValueError
        with pytest.raises(ValueError, match="Target strength must be in range"):
            VibeSelectionValidator.find_closest_reference_strength(target_strength)


class TestVibeSelectionBasic:
    """Basic unit tests for vibe selection validation."""
    
    def test_vibe_count_boundary_values(self):
        """Test boundary values for vibe count validation."""
        validator = VibeSelectionValidator()
        
        # Test exact boundaries
        assert validator.validate_vibe_count([]) is False  # 0 vibes
        assert validator.validate_vibe_count([None]) is True  # 1 vibe
        assert validator.validate_vibe_count([None] * 4) is True  # 4 vibes
        assert validator.validate_vibe_count([None] * 5) is False  # 5 vibes
    
    def test_encoding_strength_exact_values(self):
        """Test exact encoding strength values."""
        validator = VibeSelectionValidator()
        
        # Test all valid values
        for strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
            assert validator.validate_encoding_strength(strength) is True
        
        # Test some invalid values
        for strength in [0.0, 0.1, 0.6, 0.9, 1.1, 2.0]:
            assert validator.validate_encoding_strength(strength) is False
    
    def test_reference_strength_boundary_values(self):
        """Test boundary values for reference strength validation."""
        validator = VibeSelectionValidator()
        
        # Test boundaries
        assert validator.validate_reference_strength_range(0.0) is True
        assert validator.validate_reference_strength_range(1.0) is True
        assert validator.validate_reference_strength_range(-0.001) is False
        assert validator.validate_reference_strength_range(1.001) is False
    
    def test_closest_reference_strength_exact_matches(self):
        """Test closest reference strength with exact matches."""
        validator = VibeSelectionValidator()
        
        # Test exact matches
        for strength in [1.0, 0.85, 0.7, 0.5, 0.35]:
            closest = validator.find_closest_reference_strength(strength)
            assert closest == strength
    
    def test_closest_reference_strength_midpoints(self):
        """Test closest reference strength with midpoint values."""
        validator = VibeSelectionValidator()
        
        # Test midpoint between 1.0 and 0.85 (should round to closer value)
        closest = validator.find_closest_reference_strength(0.925)
        assert closest == 1.0  # 0.925 is closer to 1.0 than 0.85
        
        # Test midpoint between 0.85 and 0.7 (should round to closer value)
        closest = validator.find_closest_reference_strength(0.775)
        assert closest == 0.85  # 0.775 is closer to 0.85 than 0.7