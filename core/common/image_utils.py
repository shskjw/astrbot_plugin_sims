from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class HTMLRenderer:
    def __init__(self, template_dir: str = "resources/html"):
        # Try multiple template locations: plugin resources first, then workspace-level resources/HTML
        plugin_dir = Path(template_dir)
        # Fix: Point to the resources/HTML inside the plugin package (astrbot_plugin_sims/resources/HTML)
        # __file__ is .../core/common/image_utils.py -> parents[2] is plugin root
        workspace_dir = Path(__file__).resolve().parents[2] / "resources" / "HTML"
        if workspace_dir.exists():
            chosen = workspace_dir
        elif plugin_dir.exists():
            chosen = plugin_dir
        else:
            # Fallback to a default relative path if nothing matches
            chosen = workspace_dir
        self.template_dir = Path(chosen)
        self._env = Environment(loader=FileSystemLoader(str(self.template_dir)))

    def render(self, template_name: str, **context) -> str:
        tpl = self._env.get_template(template_name)
        return tpl.render(**context)

    def list_templates(self):
        try:
            return list(self._env.list_templates())
        except Exception:
            return []
