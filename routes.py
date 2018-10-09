"""Routes for Funding Server API."""
import os

import flasgger
import flask

import util.logger
import webserver.validation

import db
import swagger_specs


LOGGER = util.logger.logging.getLogger('pkt.funding.routes')

VERSION = swagger_specs.CONFIG['info']['version']
PORT = os.environ.get('PAKET_FUNDER_PORT', 8002)
BLUEPRINT = flask.Blueprint('funding', __name__)


def check_call_sign(key, value):
    """Raise exception if value is valid pubkey and can not be used as call sign."""
    if webserver.validation.DEBUG:
        return value
    try:
        webserver.validation.check_pubkey(key, value)
    except webserver.validation.InvalidField:
        return value
    warning = "the value of {}({}) is valid public key and can not be used as call sign".format(key, value)
    raise webserver.validation.InvalidField(warning)


# Input validators and fixers.
webserver.validation.KWARGS_CHECKERS_AND_FIXERS['_cents'] = webserver.validation.check_and_fix_natural
webserver.validation.KWARGS_CHECKERS_AND_FIXERS['call_sign'] = check_call_sign
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.authy.AuthyException] = 403
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.authy.AuthyFormatException] = 403
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.FundLimitReached] = 403
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.NotEnoughInfo] = 403
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.InvalidVerificationCode] = 403
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.InvalidPhoneNumber] = 403
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.UnknownUser] = 404
webserver.validation.CUSTOM_EXCEPTION_STATUSES[db.UserAlreadyExists] = 403


@BLUEPRINT.route("/v{}/create_user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.CREATE_USER)
@webserver.validation.call(['call_sign'], require_auth=True)
def create_user_handler(user_pubkey, call_sign):
    """
    Create a user in the system.
    """
    db.create_user(user_pubkey, call_sign)
    return {'status': 201, 'user': db.get_user(user_pubkey)}


@BLUEPRINT.route("/v{}/get_user".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.GET_USER)
@webserver.validation.call
def get_user_handler(pubkey=None, call_sign=None):
    """
    Get user details.
    """
    return {'status': 200, 'user': db.get_user(pubkey=pubkey, call_sign=call_sign)}


@BLUEPRINT.route("/v{}/user_infos".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.USER_INFOS)
@webserver.validation.call(require_auth=True)
def user_infos_handler(user_pubkey, **kwargs):
    """
    Set user details.
    """
    if kwargs:
        db.set_internal_user_info(user_pubkey, **kwargs)
    return {'status': 200, 'user_details': db.get_user_infos(user_pubkey)}


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
    Request the purchase of BULs.
    Returns an address to send ETH or BTC to.
    """
    return {'status': 201, 'payment_pubkey': db.get_payment_address(user_pubkey, euro_cents, payment_currency, 'BUL')}


@BLUEPRINT.route("/v{}/request_verification_code".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.REQUEST_VERIFICATION_CODE)
@webserver.validation.call(require_auth=True)
def request_verification_code_handler(user_pubkey):
    """
    Send verification code to user.
    """
    db.request_verification_code(user_pubkey)
    return {'status': 200, 'code_sent': True}


@BLUEPRINT.route("/v{}/verify_code".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.VERIFY_CODE)
@webserver.validation.call(['verification_code'], require_auth=True)
def verify_code_handler(user_pubkey, verification_code):
    """
    Verify code received in sms.
    """
    db.check_verification_code(user_pubkey, verification_code)
    return {'status': 200, 'verified': True}


@BLUEPRINT.route("/v{}/ratio".format(VERSION), methods=['POST'])
@flasgger.swag_from(swagger_specs.RATIO)
@webserver.validation.call(['currency'])
def ratio_handler(currency):
    """
    Get XLM/BUL price in EUR cents.
    """
    return {'status': 200, 'ratio': db.prices.bul_price() if currency == 'BUL' else db.prices.xlm_price()}


@BLUEPRINT.route("/v{}/debug/users".format(VERSION), methods=['GET'])
@flasgger.swag_from(swagger_specs.USERS)
@webserver.validation.call
def users_handler():
    """
    List all user details.
    """
    return {'status': 200, 'users': db.get_users()}
