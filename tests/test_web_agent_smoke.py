from customagents.web_agent import WebAgent

def test_visit_bill_page():
    agent = WebAgent()
    res = agent.visit("https://www.congress.gov/bill/119th-congress/house-bill/498")
    assert res.get("success") is True
    assert "title" in res
