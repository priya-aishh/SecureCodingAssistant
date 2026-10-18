from src.environment import _wikipedia_url_only


def test_url_reader_policy_accepts_sdk_wikipedia_argument_shape():
    assert _wikipedia_url_only({"Url": "https://en.wikipedia.org/w/index.php?search=Voyager+1"})
    assert _wikipedia_url_only({"Url": "https://en.wikipedia.org/wiki/Voyager_1"})
    assert not _wikipedia_url_only({"Url": "https://example.com/wiki/Voyager_1"})
    assert not _wikipedia_url_only({"Url": "http://en.wikipedia.org/wiki/Voyager_1"})
