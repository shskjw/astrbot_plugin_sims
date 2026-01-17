from ..common.image_utils import HTMLRenderer
from ..common.screenshot import html_to_image_bytes

class PoliceRenderer:
    def __init__(self):
        self.renderer = HTMLRenderer()

    def render_template(self, template_name: str, **context) -> str:
        return self.renderer.render(template_name, **context)

    async def render_image(self, template_name: str, **context) -> bytes:
        html = self.render_template(template_name, **context)
        img = await html_to_image_bytes(html, base_path=self.renderer.template_dir)
        if img:
            return img
        return html.encode('utf-8')
