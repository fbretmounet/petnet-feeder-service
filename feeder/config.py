from starlette.config import Config

config = Config(".env")

DB_DSN = config("DB_DSN", default="sqlite://gateways.db")
