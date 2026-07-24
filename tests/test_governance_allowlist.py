from fpm.governance.allowlist import host_allowed, host_of, load_allowlist


def test_host_of_extracts_hostname():
    assert host_of("https://api.llama.fi/v2/x") == "api.llama.fi"
    assert host_of("") is None


def test_load_allowlist_ignores_comments_and_blanks():
    hosts = load_allowlist("registry/_allowlist.txt")
    assert "api.llama.fi" in hosts and "api.drand.sh" in hosts
    assert all(not h.startswith("#") for h in hosts)


def test_host_allowed():
    hosts = {"api.llama.fi"}
    assert host_allowed("https://api.llama.fi/v2/x", hosts)
    assert not host_allowed("https://evil.example/x", hosts)
