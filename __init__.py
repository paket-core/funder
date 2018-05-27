"""Funding server for the PaKeT project."""
import os

import flasgger
import flask

import logger
import webserver.validation

import db
import swagger_specs

logger.setup()
LOGGER = logger.logging.getLogger('pkt.funding')

VERSION = swagger_specs.CONFIG['info']['version']
BLUEPRINT = flask.Blueprint('funding', __name__)

# FIXME should be removed soon.
db.init_db()


@BLUEPRINT.route("/v{}/create_user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.CREATE_USER)
@webserver.validation.call(['call_sign'], require_auth=True)
def create_user_handler(user_pubkey, call_sign):
    """
    Create a user in the system.
    This function will return 400 if the pubkey or the call_sign are not unique.
    """
    try:
        db.create_user(user_pubkey, call_sign)
        return {'status': 201, 'user': db.get_user(user_pubkey)}
    except AssertionError as exception:
        return {'status': 400, 'error': str(exception)}


@BLUEPRINT.route("/v{}/get_user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.GET_USER)
@webserver.validation.call
def get_user_handler(pubkey=None, call_sign=None):
    """
    Get user details.
    """
    try:
        return {'status': 200, 'user': db.get_user(pubkey=pubkey, call_sign=call_sign)}
    except db.UserNotFound as exception:
        return {'status': 404, 'error': str(exception)}


@BLUEPRINT.route("/v{}/user_infos".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.USER_INFOS)
@webserver.validation.call(require_auth=True)
def user_infos_handler(user_pubkey, **kwargs):
    """
    Set user details.
    """
    try:
        db.set_internal_user_info(user_pubkey, **kwargs)
        return {'status': 200, 'user_details': db.get_user_infos(user_pubkey)}
    except AssertionError as exception:
        return {'status': 400, 'error': str(exception)}
    except db.UserNotFound as exception:
        return {'status': 404, 'error': str(exception)}
