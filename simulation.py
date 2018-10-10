"""Simulates user activity - for debug only."""
import os
import time

import requests

import paket_stellar
import util.logger

import db

DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = util.logger.logging.getLogger('pkt.funder.routines')
TEST_LAUNCHER_SEED = os.environ.get('PAKET_TEST_LAUNCHER_SEED')
TEST_COURIER_SEED = os.environ.get('PAKET_TEST_COURIER_SEED')
TEST_RECIPIENT_SEED = os.environ.get('PAKET_TEST_RECIPIENT_SEED')
XLM_START_BALANCE = os.environ.get('PAKET_SIMULATION_XLM_START_BALANCE')
BUL_START_BALANCE = os.environ.get('PAKET_SIMULATION_BUL_START_BALANCE')
ROUTER_URL = os.environ.get('PAKET_ROUTER_URL')
BRIDGE_URL = os.environ.get('PAKET_BRIDGE_URL')


def create_new_account(user_pubkey, amount):
    """Create new Stellar account and send specified amount of XLM to it"""
    prepared_transaction = paket_stellar.prepare_create_account(paket_stellar.ISSUER, user_pubkey, amount)
    paket_stellar.submit_transaction_envelope(prepared_transaction, db.FUNDER_SEED)


def add_trust(user_pubkey, user_seed):
    """Add BUL trust to account."""
    prepared_transaction = paket_stellar.prepare_trust(user_pubkey)
    paket_stellar.submit_transaction_envelope(prepared_transaction, seed=user_seed)


def check_users():
    """
    Check if account exist in stellar and create them if not.
    Check if users exist in our system and create them if not.
    """
    for user_seed, call_sign in zip(
            (TEST_LAUNCHER_SEED, TEST_COURIER_SEED, TEST_RECIPIENT_SEED),
            ('test_launcher', 'test_courier', 'test_recipient')):
        user_keypair = paket_stellar.stellar_base.Keypair.from_seed(user_seed)
        user_pubkey = user_keypair.address().decode()
        user_seed = user_keypair.seed().decode()
        try:
            paket_stellar.get_bul_account(user_pubkey)
        except paket_stellar.stellar_base.address.AccountNotExistError:
            LOGGER.info("creating account %s", user_pubkey)
            create_new_account(user_pubkey, XLM_START_BALANCE)
            LOGGER.info("adding trust to %s", user_pubkey)
            add_trust(user_pubkey, user_seed)
            paket_stellar.fund_from_issuer(user_pubkey, BUL_START_BALANCE)
        except paket_stellar.TrustError:
            LOGGER.info("adding trust to %s", user_pubkey)
            add_trust(user_pubkey, user_seed)
            paket_stellar.fund_from_issuer(user_pubkey, BUL_START_BALANCE)

        try:
            db.create_user(user_pubkey, call_sign)
        except db.UserAlreadyExists as exc:
            LOGGER.info(str(exc))


def simulation_routine():
    """Simulates user activity - for debug only."""
    if not DEBUG:
        LOGGER.error('simulation user activity allowed only in debug mode')
        return

    check_users()
    for user_routine in ():
        if user_routine():
            break