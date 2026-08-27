from researchflow.app_factory import create_app
from researchflow.core.logging import configure_logging

configure_logging()
app = create_app()
