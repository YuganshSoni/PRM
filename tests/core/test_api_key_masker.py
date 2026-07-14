from server.core.api_key_masker import ApiKeyMasker


def test_mask_returns_constant_for_non_empty_key():
    assert ApiKeyMasker.mask("sk-live-abcdef") == ApiKeyMasker.MASK
    assert ApiKeyMasker.mask("x") == "****************************"


def test_mask_returns_empty_string_for_blank_key():
    assert ApiKeyMasker.mask("") == ""
    assert ApiKeyMasker.mask("   ") == ""
    assert ApiKeyMasker.mask("\t\n") == ""
