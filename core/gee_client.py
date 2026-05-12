import ee
import os
from . import utils

def get_ee_client():
    """Retorna el cliente de Earth Engine inicializado"""
    success, msg = utils.init_gee_session()
    if success:
        return ee
    else:
        raise ConnectionError(msg)
