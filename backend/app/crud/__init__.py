"""Domain-split CRUD layer. Re-exported flat so `crud.<fn>` keeps working."""
from app.crud.base import *  # noqa: F401,F403
from app.crud.users import *  # noqa: F401,F403
from app.crud.workspaces import *  # noqa: F401,F403
from app.crud.invites import *  # noqa: F401,F403
from app.crud.audit import *  # noqa: F401,F403
from app.crud.categories import *  # noqa: F401,F403
from app.crud.products import *  # noqa: F401,F403
from app.crud.replenishment import *  # noqa: F401,F403
from app.crud.stock import *  # noqa: F401,F403
from app.crud.search import *  # noqa: F401,F403
from app.crud.dashboard import *  # noqa: F401,F403
