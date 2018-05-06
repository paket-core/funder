#!/usr/bin/env python3
"""Identity server for the PaKeT project."""
import flasgger
import flask

import logger
import webserver.validation

import db
import swagger_specs

logger.setup()
LOGGER = logger.logging.getLogger('pkt.identity')

VERSION = swagger_specs.CONFIG['info']['version']
BLUEPRINT = flask.Blueprint('identity', __name__)

# This should be removed soon.
db.init_db()


@BLUEPRINT.route("/v{}/add_user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.ADD_USER)
@webserver.validation.call(['full_name', 'phone_number', 'address', 'paket_user'], require_auth=True)
def add_user_handler(user_pubkey, full_name, phone_number, address, paket_user):
    """
    Add user details
    Register a user in the identity server.
    This function will return 400 if the pubkey doesn't belong to a valid stellar account that trusts receiving BULs.
    ---
    """
    db.create_user(user_pubkey, full_name, phone_number, address, paket_user)
    return {'status': 201, 'user': db.get_user(user_pubkey)}


@BLUEPRINT.route("/v{}/get_user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.GET_USER)
@webserver.validation.call(require_auth=True)
def get_user_handler(user_pubkey, queried_pubkey=None):
    """
    Get user details
    Returns available user info.
    Only Authorized user can receive this information. Use the Authorize function to permit a specific user.
    ---
    """
    if queried_pubkey is None:
        queried_pubkey = user_pubkey
    elif queried_pubkey != user_pubkey:
        assert db.is_authorized(user_pubkey, queried_pubkey), "pubkey {} is not authorized to view {}".format(
            user_pubkey, queried_pubkey)
    return {'status': 200, 'user': db.get_user(queried_pubkey)}


@BLUEPRINT.route("/v{}/authorize".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.AUTHORIZE)
@webserver.validation.call(['authorized_pubkey'], require_auth=True)
def authorize_handler(user_pubkey, authorized_pubkey):
    """
    Authorize a user to view user_pubkey's details
    A user can permit a another user to receive information about him.
    The authorization is done for a pubkey and no check is made on the validity or availability of the pubkey.
    Typically a user will only authorize the PaKeT funding user.
    ---
    """
    db.add_authorization(authorized_pubkey, user_pubkey)
    return {'status': 201}


@BLUEPRINT.route("/v{}/unauthorize".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.UNAUTHORIZE)
@webserver.validation.call(['authorized_pubkey'], require_auth=True)
def unauthorize_handler(user_pubkey, authorized_pubkey):
    """
    Unauthorize a user to view user_pubkey's details

    ---
    """
    db.remove_authorization(authorized_pubkey, user_pubkey)
    return {'status': 201}


if __name__ == '__main__':
    webserver.run(BLUEPRINT, swagger_specs.CONFIG)
