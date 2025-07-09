config = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "simple": {
            "()": "pulsemeeter.logger.log_config.FormatLog",
            "format": "[%(levelname)s]: %(message)s",
            "datefmt": "%H:%M:%S"
        },

        "default": {
            "()": "pulsemeeter.logger.log_config.FormatLog",
            "format": "[%(asctime)s] [%(levelname)s]: %(message)s",
            "datefmt": "%H:%M:%S"
        },

        "debug": {
            "()": "pulsemeeter.logger.log_config.FormatLog",
            "format": "[%(asctime)s] [%(levelname)s] in [%(module)s@%(funcName)s]: %(message)s",
            "datefmt": "%y/%m/%Y %H:%M:%S"
        }
    },

    "filters": {
        "info_and_below": {
            "()": "pulsemeeter.logger.log_config.filter_maker",
            "max_level": "INFO"
        }
    },

    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "default",
            "stream": "ext://sys.stdout",
            "filters": ["info_and_below"]
        },

        "stderr": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "default",
            "stream": "ext://sys.stderr"
        }
    },

    "loggers": {
        "root": {
            "level": "INFO",
            "handlers": ["stdout", "stderr"]
        },

        "generic": {
            "level": "INFO"
        }

    }
}
