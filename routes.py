"""Routes for Funding Server API."""
import flasgger
import flask

import util.logger
import webserver.validation

import db
import swagger_specs

util.logger.setup()
LOGGER = util.logger.logging.getLogger('pkt.funding.routes')

VERSION = swagger_specs.CONFIG['info']['version']
BLUEPRINT = flask.Blueprint('funding', __name__)


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
        return {'status': 200, 'user_details': db.set_internal_user_info(user_pubkey, **kwargs)}
    except AssertionError as exception:
        return {'status': 400, 'error': str(exception)}
    except db.UserNotFound as exception:
        return {'status': 404, 'error': str(exception)}


@BLUEPRINT.route("/v{}/create_stellar_account".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.CREATE_STELLAR_ACCOUNT)
@webserver.validation.call(['payment_currency'], require_auth=True)
def create_stellar_account_handler(user_pubkey, payment_currency):
    """
    Request the creation of a Stellar account.
    Returns an address to send ETH or BTC to.
    """
    return {'status': 201, 'payment_pubkey': db.get_payment_address(user_pubkey, 500, payment_currency, 'XLM')}


@BLUEPRINT.route("/v{}/purchase_xlm".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.PURCHASE_XLM)
@webserver.validation.call(['euro_cents', 'payment_currency'], require_auth=True)
def purchase_xlm_handler(user_pubkey, euro_cents, payment_currency):
    """
    Request the purchase of Stellar lumens.
    Returns an address to send ETH or BTC to.
    """
    return {'status': 201, 'payment_pubkey': db.get_payment_address(user_pubkey, euro_cents, payment_currency, 'XLM')}


@BLUEPRINT.route("/v{}/purchase_bul".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.PURCHASE_BUL)
@webserver.validation.call(['euro_cents', 'payment_currency'], require_auth=True)
def purchase_bul_handler(user_pubkey, euro_cents, payment_currency):
    """
    Request the purchase of Stellar lumens.
    Returns an address to send ETH or BTC to.
    """
    return {'status': 201, 'payment_pubkey': db.get_payment_address(user_pubkey, euro_cents, payment_currency, 'BUL')}


@BLUEPRINT.route("/v{}/debug/users".format(VERSION), methods=['GET'])
@flasgger.swag_from(swagger_specs.USERS)
@webserver.validation.call
def users_handler():
    """
    List all user details.
    """
    return {'status': 200, 'users': db.get_users()}
