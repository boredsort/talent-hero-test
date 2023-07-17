import logging
from utils.constants import Defaults

logger = logging.getLogger(__name__)

def attribute(func):
    def wrapper(*args, **kwargs):
        try:
            func_name = func.__name__
            logger.debug(f'Execute {func_name}')
            value = func(*args, **kwargs)

            if not value:
                value = Defaults.NOT_FOUND

        except Exception as e:
            logging.debug('Failed on ' + func_name  )
            logging.debug(str(e))
            value = Defaults.ERROR

        return value
    
    return wrapper