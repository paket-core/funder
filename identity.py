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


@BLUEPRINT.route("/v{}/user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.USER_POST)
@webserver.validation.call(['full_name', 'phone_number', 'address', 'paket_user'], require_auth=True)
def user_post_handler(user_pubkey, full_name, phone_number, address, paket_user):
    """Add user details."""
    db.create_user(user_pubkey, full_name, phone_number, address, paket_user)
    return {'status': 201, 'user': db.get_user(user_pubkey)}


@BLUEPRINT.route("/v{}/user".format(VERSION), methods=['GET'])
@flasgger.swag_from(swagger_specs.USER_GET)
@webserver.validation.call(require_auth=True)
def user_get_handler(user_pubkey, queried_pubkey=None):
    """Get user details."""
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
    """Authorize a pubkey to view user_pubkey's details."""
    db.add_authorization(authorized_pubkey, user_pubkey)
    return {'status': 201}


@BLUEPRINT.route("/v{}/unauthorize".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.UNAUTHORIZE)
@webserver.validation.call(['authorized_pubkey'], require_auth=True)
def unauthorize_handler(user_pubkey, authorized_pubkey):
    """Unauthorize a pubkey to view user_pubkey's details."""
    db.remove_authorization(authorized_pubkey, user_pubkey)
    return {'status': 201}


if __name__ == '__main__':
    webserver.run(BLUEPRINT, swagger_specs.CONFIG)
