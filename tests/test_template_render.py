from core.common.image_utils import HTMLRenderer


def test_templates_list_and_render():
    r = HTMLRenderer()
    tpls = r.list_templates()
    # Just assert listing doesn't crash
    assert isinstance(tpls, list)
    # If user_info.html exists, try rendering
    if "user_info.html" in tpls:
        html = r.render("user_info.html", user={"name":"测试用户","money":100})
        assert "测试用户" in html or "100" in html
