from mysql.connector import connect, Error
from .config import Config

def get_connection(autocommit: bool = True):
    config = Config()
    db_conf = {
        "host": config.tidb_host,
        "port": config.tidb_port,
        "user": config.tidb_user,
        "password": config.tidb_password,
        "database": config.tidb_db_name,
        "autocommit": autocommit,
        "use_pure": True,  # pure Python driver for cross-platform
    }

    if config.ca_path:
        db_conf["ssl_verify_cert"] = True
        db_conf["ssl_verify_identity"] = True
        db_conf["ssl_ca"] = config.ca_path
    else:
        # Enables SSL using default CA certs
        db_conf["ssl_disabled"] = False

    return connect(**db_conf)
