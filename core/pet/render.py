from pathlib import Path
from jinja2 import Environment, FileSystemLoader

class PetRenderer:
    def __init__(self):
        # Point to the pet-specific templates directory
        # __file__ is .../core/pet/render.py -> parents[2] is plugin root
        pet_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "pet"
        
        if not pet_templates_dir.exists():
            # Fallback to HTML directory if pet templates don't exist
            pet_templates_dir = Path(__file__).resolve().parents[2] / "resources" / "HTML"
        
        self.template_dir = pet_templates_dir
        self._env = Environment(loader=FileSystemLoader(str(self.template_dir)))

    def render_template(self, template_name: str, **context) -> str:
        # Add resource path for templates to load CSS/fonts
        context['_res_path'] = '../'
        context['cssFile'] = '../CSS/'
        tpl = self._env.get_template(template_name)
        return tpl.render(**context)

    def render_my_pets(self, pets: list):
        # Need template resources/HTML/my_pets.html
        return self.render_template("my_pets.html", pets=pets)

    def render_draw(self, pet):
        return self.render_template("pet_draw.html", pet=pet)

    def render_status(self, pet):
        return self.render_template("pet_status.html", pet=pet)
