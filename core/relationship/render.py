from ..common.image_utils import HTMLRenderer

class RelationshipRenderer:
    def __init__(self):
        self.renderer = HTMLRenderer()

    def render_status(self, relationship):
        # Convert model to dict for template if needed, or pass object directly if jinja can handle it.
        # Jinja handles objects fine.
        # But we need to ensure property names match template expectations (targetName vs target_name)
        # Template uses `targetName`. Model uses `target_name`.
        # I'll convert it here or change template. Changing data passed is safer.
        data = relationship.to_dict()
        data['targetName'] = relationship.target_name # Map snake_case to camelCase
        return self.renderer.render("relationship_status.html", relationship=data)
