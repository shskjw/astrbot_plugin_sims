from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..common.screenshot import html_to_image_bytes

class PoliceRenderer:
    def __init__(self):
        # Point to the police-specific templates directory
        # __file__ is .../core/police/render.py -> parents[2] is plugin root
        police_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "police"
        
        if not police_templates_dir.exists():
            # Fallback to HTML directory if police templates don't exist
            police_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "HTML"
        
        self.template_dir = police_templates_dir
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
        return html.encode('utf-8')
