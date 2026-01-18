from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..common.screenshot import html_to_image_bytes

class FarmRenderer:
    def __init__(self):
        # Point to the farm-specific templates directory
        # __file__ is .../core/farm/render.py -> parents[2] is plugin root
        farm_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "farm"
        
        if not farm_templates_dir.exists():
            # Fallback to HTML directory if farm templates don't exist
            farm_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "HTML"
        
        self.template_dir = farm_templates_dir
        self._env = Environment(loader=FileSystemLoader(str(self.template_dir)))

    def render_template(self, template_name: str, **context) -> str:
        # Add resource path for templates to load CSS/fonts
        context['_res_path'] = '../'
        context['cssFile'] = '../CSS/'
        tpl = self._env.get_template(template_name)
        return tpl.render(**context)

    async def render_image(self, template_name: str, **context) -> bytes:
        html = self.render_template(template_name, **context)
        img = await html_to_image_bytes(html, base_path=self.template_dir)
        if img:
            return img
        # Fallback: return HTML encoded as bytes (so caller can still see content)
        return html.encode('utf-8')
