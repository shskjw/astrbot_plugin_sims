from ..common.image_utils import HTMLRenderer

class PetRenderer:
    def __init__(self):
        self.renderer = HTMLRenderer()

    def render_my_pets(self, pets: list):
        # Need template resources/HTML/my_pets.html
        return self.renderer.render("my_pets.html", pets=pets)

    def render_draw(self, pet):
        return self.renderer.render("pet_draw.html", pet=pet)

    def render_status(self, pet):
        return self.renderer.render("pet_status.html", pet=pet)
