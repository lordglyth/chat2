from tracefox.scanner import classify_response, extract_metadata, normalize_username


def test_normalize_username():
    assert normalize_username(" @wondervaylor ") == "wondervaylor"


def test_classify_found_and_missing():
    site = {"e_code": 200, "e_string": "PROFILE_OK", "m_code": 404, "m_string": ""}
    assert classify_response(site, 200, "xx PROFILE_OK yy") == "found"
    assert classify_response(site, 404, "not here") == "not_found"
    assert classify_response(site, 200, "wrong page") == "unknown"


def test_extract_metadata():
    html = '''<html><head><title>Wonder Vaylor</title><meta name="description" content="hello wondervaylor"><meta property="og:image" content="https://x.test/a.png"><link rel="canonical" href="https://x.test/wondervaylor"></head></html>'''
    meta = extract_metadata(html, "https://x.test/wondervaylor", "wondervaylor")
    assert meta["title"] == "Wonder Vaylor"
    assert meta["username_visible"] is True
    assert meta["avatar"].endswith("a.png")
