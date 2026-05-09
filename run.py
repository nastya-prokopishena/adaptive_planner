import os

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from backend.app import create_app
from backend.infrastructure.db.database import engine
from backend.infrastructure.db.models import Base

app = create_app()

Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)