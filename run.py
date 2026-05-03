import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from backend.app import create_app

# ⬇️ ДОДАЙ
from backend.infrastructure.db.database import engine
from backend.infrastructure.db.models import Base
from backend.infrastructure.db import models
import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = create_app()

# ⬇️ ДОДАЙ
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    app.run(debug=True)