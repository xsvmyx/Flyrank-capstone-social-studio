import pytest
from services.agents.facebook_agent import FacebookAgent
from services.agents.linkedin_agent import LinkedInAgent


@pytest.fixture
def linkedin_agent():
    return LinkedInAgent()


@pytest.fixture
def facebook_agent():
    return FacebookAgent()


# ==========================================
# 1. Empty & Whitespace Validation Tests
# ==========================================

def test_empty_content_blocked(linkedin_agent, facebook_agent):
    for bad_content in ["", "   ", "\n\t "]:
        is_valid_li, err_li = linkedin_agent.validate(bad_content)
        is_valid_fb, err_fb = facebook_agent.validate(bad_content)

        assert is_valid_li is False
        assert err_li == "Content is empty."
        assert is_valid_fb is False
        assert err_fb == "Content is empty."


# ==========================================
# 2. Length & Boundary Constraint Tests
# ==========================================

def test_linkedin_blocked_when_too_short(linkedin_agent):
    bad_variant = "Too short"
    is_valid, error_msg = linkedin_agent.validate(bad_variant)
    
    assert is_valid is False
    assert "Length (9 chars) outside range [30-3000]" in error_msg


def test_linkedin_blocked_when_29_chars_boundary(linkedin_agent):
    bad_variant = "A" * 29
    is_valid, error_msg = linkedin_agent.validate(bad_variant)

    assert is_valid is False
    assert "Length (29 chars) outside range [30-3000]" in error_msg


def test_linkedin_passed_exact_30_chars_boundary(linkedin_agent):
    good_variant = "Valid post with 30 chars #Tech"
    assert len(good_variant) >= 30
    is_valid, error_msg = linkedin_agent.validate(good_variant)

    assert is_valid is True
    assert error_msg is None


def test_linkedin_blocked_when_too_long(linkedin_agent):
    bad_variant = ("A" * 3001) + " #AI"
    is_valid, error_msg = linkedin_agent.validate(bad_variant)
    
    assert is_valid is False
    assert "outside range [30-3000]" in error_msg


def test_facebook_blocked_when_exceeds_2000_chars(facebook_agent):
    bad_variant = ("This is a very long Facebook post. " * 70) + " #Tech"
    assert len(bad_variant) > 2000

    is_valid, error_msg = facebook_agent.validate(bad_variant)

    assert is_valid is False
    assert "outside range [30-2000]" in error_msg


# ==========================================
# 3. Tone & Forbidden Meta-text Tests (Inc. Case Insensitivity)
# ==========================================

def test_linkedin_blocked_when_ai_placeholder_present(linkedin_agent):
    bad_variant = "As an AI, here is your post about leadership in tech. #Leadership"
    is_valid, error_msg = linkedin_agent.validate(bad_variant)

    assert is_valid is False
    assert "Forbidden placeholder(s) detected:" in error_msg
    assert "'as an ai'" in error_msg


def test_facebook_blocked_when_bracket_placeholder_present(facebook_agent):
    bad_variant = "Check out our new update! [insert link here] #Update"
    is_valid, error_msg = facebook_agent.validate(bad_variant)

    assert is_valid is False
    assert "Forbidden placeholder(s) detected:" in error_msg
    assert "'[insert'" in error_msg


def test_case_insensitive_forbidden_placeholders(linkedin_agent):
    bad_variants = [
        "HERE IS YOUR POST for today's announcement. #News",
        "Bonjour [VOTRE NOM], voici votre article. #Marketing",
        "AS AN AI language model, I recommend this. #AI",
    ]

    for bad_variant in bad_variants:
        is_valid, error_msg = linkedin_agent.validate(bad_variant)
        assert is_valid is False
        assert "Forbidden placeholder(s) detected:" in error_msg


# ==========================================
# 4. Hashtag Count Constraint Tests
# ==========================================

def test_linkedin_blocked_when_no_hashtags(linkedin_agent):
    bad_variant = "This is a great professional post with sufficient character length, but it misses hashtags."
    is_valid, error_msg = linkedin_agent.validate(bad_variant)

    assert is_valid is False
    assert "Hashtag count (0) outside range [1-10]" in error_msg


def test_linkedin_blocked_when_too_many_hashtags(linkedin_agent):
    bad_variant = (
        "Great insights on tech leadership!\n\n"
        "#one #two #three #four #five #six #seven #eight #nine #ten #eleven"
    )
    is_valid, error_msg = linkedin_agent.validate(bad_variant)

    assert is_valid is False
    assert "Hashtag count (11) outside range [1-10]" in error_msg


def test_facebook_blocked_when_too_many_hashtags(facebook_agent):
    bad_variant = (
        "Join our community discussion today! We love connecting with everyone.\n\n"
        "#one #two #three #four #five #six #seven"
    )
    is_valid, error_msg = facebook_agent.validate(bad_variant)

    assert is_valid is False
    assert "Hashtag count (7) outside range [0-5]" in error_msg


# ==========================================
# 5. Structure & Single Paragraph Rule Tests
# ==========================================

def test_single_paragraph_too_long_blocked(linkedin_agent):
    # Text > 300 chars without any line breaks (\n)
    single_block = (
        "This is a very long continuous paragraph without any line breaks or bullet points. "
        "LinkedIn algorithms and readers strongly prefer short, scannable paragraphs with clear spacing. "
        "When an AI generates a single massive wall of text that exceeds three hundred characters without a single line break, "
        "our custom deterministic validator catches it and rejects it immediately. #Formatting"
    )
    assert len(single_block) > 300
    assert "\n" not in single_block

    is_valid, error_msg = linkedin_agent.validate(single_block)

    assert is_valid is False
    assert "Text is too long (>300 chars) to consist of a single paragraph." in error_msg


# ==========================================
# 6. Multiple Simultaneous Violations Test
# ==========================================

def test_multiple_simultaneous_violations_accumulated(linkedin_agent):
    # Short length + forbidden placeholder + missing hashtag
    bad_variant = "As an AI..."
    is_valid, error_msg = linkedin_agent.validate(bad_variant)

    assert is_valid is False
    # All errors must be concatenated with ' | '
    assert " | " in error_msg
    assert "Length (11 chars) outside range [30-3000]" in error_msg
    assert "Forbidden placeholder(s) detected: 'as an ai'" in error_msg
    assert "Hashtag count (0) outside range [1-10]" in error_msg


# ==========================================
# 7. Valid Variant Control Tests
# ==========================================

def test_linkedin_valid_variant_passed(linkedin_agent):
    good_variant = (
        "Excited to share insights on modern web development practices!\n\n"
        "What are your favorite tools in 2026? Let us know below.\n\n"
        "#WebDev #Tech #SoftwareEngineering"
    )
    is_valid, error_msg = linkedin_agent.validate(good_variant)

    assert is_valid is True
    assert error_msg is None


def test_facebook_valid_variant_passed(facebook_agent):
    good_variant = (
        "Happy Friday everyone! 🎉\n\n"
        "What are your plans for the weekend? Drop a comment below!\n\n"
        "#Community #Weekend"
    )
    is_valid, error_msg = facebook_agent.validate(good_variant)

    assert is_valid is True
    assert error_msg is None
