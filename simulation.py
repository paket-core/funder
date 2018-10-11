"""Simulates user activity - for debug only."""
import json
import os
import random
import time

import requests

import paket_stellar
import util.logger
import util.distance

import db

DEBUG = bool(os.environ.get('PAKET_DEBUG'))
LOGGER = util.logger.logging.getLogger('pkt.funder.routines')
TEST_LAUNCHER_SEED = os.environ.get('PAKET_TEST_LAUNCHER_SEED')
TEST_LAUNCHER_PUBKEY = paket_stellar.stellar_base.Keypair.from_seed(TEST_LAUNCHER_SEED)
TEST_COURIER_SEED = os.environ.get('PAKET_TEST_COURIER_SEED')
TEST_COURIER_PUBKEY = paket_stellar.stellar_base.Keypair.from_seed(TEST_COURIER_SEED)
TEST_RECIPIENT_SEED = os.environ.get('PAKET_TEST_RECIPIENT_SEED')
TEST_RECIPIENT_PUBKEY = paket_stellar.stellar_base.Keypair.from_seed(TEST_RECIPIENT_SEED)
XLM_START_BALANCE = os.environ.get('PAKET_SIMULATION_XLM_START_BALANCE')
BUL_START_BALANCE = os.environ.get('PAKET_SIMULATION_BUL_START_BALANCE')
ROUTER_URL = os.environ.get('PAKET_ROUTER_URL')
BRIDGE_URL = os.environ.get('PAKET_BRIDGE_URL')
PAYMENT = 5000000
COLLATERAL = 10000000
LOCATIONS = {
    'from': [
        ('49.9944226,36.1646005', 'Nyzhnya Hyivska St 142 KharkivKharkivska oblast'),
        ('52.3618169,16.9324558', 'Nad Starynka 18 61-361 Poznan Poland'),
        ('-4.0541548,39.6965244', 'Nyali Mombasa Kenya'),
        ('-16.366137,-48.9398591', 'R. 6 Q 12 31 - Jardim Arco Verde Brazil'),
        ('34.023181,-94.7417068', '411 W Slater St Broken Bow OK 74728 USA'),
        ('11.3334285,108.8717923', 'Phuoc Diem Ninh Thuan Province Vietnam')],
    'to': [
        ('49.2935249,-123.1375815', '1960 Alberni St #804 Vancouver BC V6G 1B4 Canada'),
        ('-35.4198461,149.0681731', '320 Reed St Canberra Australian Capital Territory Australia'),
        ('33.8553049,130.8657624', '3 Chome-20-2 Kumagai Kitakyushu Fukuoka Prefecture Japan'),
        ('29.4159592,106.9277615', 'Banan Chongqing China'),
        ('32.0125571,34.7389795', 'Bat Yam Israel'),
        ('-34.2014474,24.8263067', 'Cape St Francis 6313 South Africa')]}


class SimulationError(Exception):
    """Can't perform actions during simulation."""


def create_new_account(source_account_seed, user_pubkey, amount):
    """Create new Stellar account and send specified amount of XLM to it."""
    source_keypair = paket_stellar.stellar_base.Keypair.from_seed(source_account_seed)
    prepared_transaction = paket_stellar.prepare_create_account(
        source_keypair.address().decode(), user_pubkey, amount)
    paket_stellar.submit_transaction_envelope(prepared_transaction, source_account_seed)


def add_trust(user_pubkey, user_seed):
    """Add BUL trust to account."""
    prepared_transaction = paket_stellar.prepare_trust(user_pubkey)
    paket_stellar.submit_transaction_envelope(prepared_transaction, seed=user_seed)


def call(api_url, path, user_pubkey=None, **kwargs):
    """Post data to API server."""
    LOGGER.info("calling %s", path)
    headers = {'Pubkey': user_pubkey} if user_pubkey is not None else None
    response = requests.post("{}/{}".format(api_url, path), headers=headers, data=kwargs).json()
    if response['status'] != 200:
        raise SimulationError(response['error'])
    return response


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
            create_new_account(db.FUNDER_SEED, user_pubkey, XLM_START_BALANCE)
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


def launch_new_package(package_number):
    """Launch new package."""
    escrow_keypair = paket_stellar.stellar_base.Keypair.random()
    escrow_pubkey = escrow_keypair.address().decode()
    escrow_seed = escrow_keypair.seed().decode()
    from_ = random.choice(LOCATIONS['from'])
    to = random.choice(LOCATIONS['to'])
    package = {
        'escrow_pubkey': escrow_pubkey,
        'recipient_pubkey': TEST_RECIPIENT_PUBKEY,
        'launcher_phone_number': '+40534591250',
        'recipient_phone_number': '+40544516250',
        'payment_buls': PAYMENT,
        'collateral_buls': COLLATERAL,
        'deadline_timestamp': time.time() + 60 * 60 * 24 * 2,
        'description': "Test package number {}".format(package_number),
        'from_location': from_[0],
        'to_location': to[0],
        'from_address': from_[1],
        'to_address': to[1],
        'event_location': from_[0]}
    call(ROUTER_URL, 'create_package', TEST_LAUNCHER_PUBKEY, **package)
    event = {
        'event_type': 'escrow seed added',
        'location': from_[0],
        'escrow_pubkey': escrow_pubkey,
        'kwargs': '{"escrow_seed": {}}'.format(escrow_seed)}
    call(ROUTER_URL, 'add_event', TEST_LAUNCHER_PUBKEY, **event)


def launcher_action():
    """
    Check if launcher has packages to deliver. If no - launch new package.
    :return main_action_performed: True if main user action - launching package - has been performed.
    """
    response = call(ROUTER_URL, 'my_packages', TEST_LAUNCHER_PUBKEY)
    packages = response['packages']

    if not packages or all((package['status'] == 'delivered' for package in packages)):
        launch_new_package(len(packages) + 1)
        return True

    return False


def courier_action():
    """
    Check if some packages available for delivery. If yes - accept them like courier.
    Send `changed location` event if courier has active package.
    :return main_action_performed: True if main user action - accepting package - has been performed.
    """
    response = call(ROUTER_URL, 'my_packages', TEST_COURIER_PUBKEY)
    packages = response['packages']

    in_transit_package = next((package for package in packages if package['status'] == 'in transit'))
    if in_transit_package is not None:
        # TODO: send `location changed` event
        return False

    waiting_pickup_package = next((package for package in packages if package['status'] == 'waiting pickup'))
    if waiting_pickup_package is not None:
        escrow_pubkey = waiting_pickup_package['escrow_pubkey']
        seed_event = next((event for event in waiting_pickup_package['events']
                           if event['event_type'] == 'escrow seed added'))
        if seed_event is None:
            raise SimulationError("package {} is not simulation pacakge".format(escrow_pubkey))
        escrow_seed = json.loads(seed_event['kwargs'])['escrow_seed']
        call(
            ROUTER_URL, 'confirm_couriering', TEST_COURIER_PUBKEY,
            escrow_pubkey=escrow_pubkey, location=waiting_pickup_package['from_location'])
        create_new_account(TEST_LAUNCHER_SEED, escrow_pubkey, 50000000)
        add_trust(escrow_pubkey, escrow_seed)
        escrow = paket_stellar.prepare_escrow(
            escrow_pubkey, TEST_LAUNCHER_PUBKEY, TEST_COURIER_PUBKEY,
            TEST_RECIPIENT_PUBKEY, PAYMENT, COLLATERAL, waiting_pickup_package['deadline'])
        paket_stellar.submit_transaction_envelope(escrow['set_options_transaction'], escrow_seed)
        send_bul_transaction = paket_stellar.prepare_send_buls(TEST_LAUNCHER_PUBKEY, escrow_pubkey, PAYMENT)
        paket_stellar.submit_transaction_envelope(send_bul_transaction, TEST_LAUNCHER_SEED)
        send_bul_transaction = paket_stellar.prepare_send_buls(TEST_COURIER_PUBKEY, escrow_pubkey, COLLATERAL)
        paket_stellar.submit_transaction_envelope(send_bul_transaction, TEST_COURIER_SEED)
        call(
            ROUTER_URL, 'accept_package', TEST_COURIER_PUBKEY,
            escrow_pubkey=escrow_pubkey, location=in_transit_package['from_location'])
        return True

    return False


def recipient_action():
    """
    Accept package if it near by recipient location.
    :return main_action_performed: True if main user action - accepting package - has been performed.
    """
    response = call(ROUTER_URL, 'my_packages', TEST_RECIPIENT_PUBKEY)
    packages = response['packages']

    in_transit_package = next((package for package in packages if package['status'] == 'in transit'))
    if in_transit_package is not None:
        current_location = [event for event in in_transit_package['events']
                            if event['event_type'] == 'location changed'][-1]
        distance = util.distance.haversine(current_location, in_transit_package['to_location'])
        if distance < 2:
            call(
                ROUTER_URL, 'accept_package', TEST_RECIPIENT_PUBKEY,
                escrow_pubkey=in_transit_package['escrow_pubkey'], location=in_transit_package['to_location'])
            return True

    return False


def simulation_routine():
    """Simulates user activity - for debug only."""
    if not DEBUG:
        LOGGER.error('simulation user activity allowed only in debug mode')
        return

    check_users()
    for action in (launcher_action, courier_action, recipient_action):
        if action():
            break
