"""Print the API's OpenAPI document as JSON (used to generate packages/types).

Builds the schema from the app object without starting a server or touching the database.
"""

import json
import sys

from app.core.config import AppEnv, Settings
from app.main import create_app


def main() -> None:
    app = create_app(Settings(_env_file=None, app_env=AppEnv.LOCAL, log_level="WARNING"))
    json.dump(app.openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
