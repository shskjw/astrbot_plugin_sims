from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..common.screenshot import html_to_image_bytes

class CinemaRenderer:
    def __init__(self):
        # Point to the cinema-specific templates directory
        # __file__ is .../core/cinema/render.py -> parents[2] is plugin root
        cinema_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "cinema"
        
        if not cinema_templates_dir.exists():
            # Fallback to HTML directory if cinema templates don't exist
            cinema_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "HTML"
        
        self.template_dir = cinema_templates_dir
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
        return img or html.encode('utf-8')
