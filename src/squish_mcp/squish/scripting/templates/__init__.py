from pathlib import Path
from string import Template


def get_template(template_name: str) -> Template:
    template_path = Path(__file__).parent / template_name
    with template_path.open() as f:
        return Template(f.read())
