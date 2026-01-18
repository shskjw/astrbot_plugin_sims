from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from ..common.screenshot import html_to_image_bytes

class RelationshipRenderer:
    def __init__(self):
        # Point to the relationship-specific templates directory
        # __file__ is .../core/relationship/render.py -> parents[2] is plugin root
        relationship_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "relationship"
        
        if not relationship_templates_dir.exists():
            # Fallback to HTML directory if relationship templates don't exist
            relationship_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "HTML"
        
        self.template_dir = relationship_templates_dir
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
        # Fallback: return HTML encoded as bytes
        return html.encode('utf-8')
    
    def render_status(self, relationship) -> str:
        # Convert model to dict and map snake_case to camelCase
        data = relationship.to_dict() if hasattr(relationship, 'to_dict') else relationship
        data['targetName'] = relationship.target_name if hasattr(relationship, 'target_name') else data.get('target_name', '')
        return self.render_template("relationship_status.html", relationship=data)
