"""Swagger specifications of Funding Server."""
VERSION = 2
CONFIG = {
    'title': 'PaKeT funding API',
    'uiversion': 2,
    'specs_route': '/',
    'specs': [{
        'endpoint': '/',
        'route': '/apispec.json',
    }],
    'info': {
        'title': 'The PaKeT Funding Server API',
        'version': VERSION,
        'contact': {
            'name': 'The PaKeT Project',
            'email': 'israel@paket.global',
            'url': 'https://fund.paket.global',
        },
        'license': {
            'name': 'GNU GPL 3.0',
            'url': 'http://www.gnu.org/licenses/'
        },
        'description': '''

The Funding server is responsible for giving users a simple way to create
Stellar accounts, purchase XLMs used to pay for the Stellar transactions, and
BULs used to launch packages.

This requires user registration, so we can perform KYC/AML checks.

A secondary function of the Funding server is an internal identity server,
which resolves a unique call sign to a public key and Stellar address.

Security
========
Our calls are split into the following security levels:
 - Debug functions: require no authentication, available only in debug mode.
 - Anonymous functions: require no authentication, used to retrieve public data.
 - Authenticated functions: require asymmetric key authentication:
    - The **'Pubkey'** header will contain the user's pubkey.
    - The **'Fingerprint'** header is constructed from the comma separated
      concatenation of the called URI, all the arguments (as key=value), and an
      ever increasing nonce (recommended to use Unix time in milliseconds).
    - The **'Signature'** header will contain a Base64 ASCII encoded signature
      on the specified 'Fingerprint', produced by the private key corresponding
      to the specified 'pubkey'.

Note, that the security headers are not validated when in debug mode, but the
server still expects some values to be passed.

Currency Denomination
=====================
All currency amounts are denominated in integers of their indivisible units.
That means that when referring to an amount of EUR we will always use EUR cents
(1/100 EUR), when referring to Stellar assets (BUL and XLM) we will be using
stroops (1/10^7 XLM or BUL), when referring to BTC we will use satoshis
(1/10^8 BTC), and when referring to ETH we will use wei (1/10^18 ETH).

The API
======='''}}

CREATE_USER = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'call_sign', 'in': 'formData', 'required': True, 'type': 'string'}],
    'responses': {
        '201': {'description': 'user created'},
        '400': {'description': 'bad Request: pubkey or call_sign are not unique'}}}

GET_USER = {
    'parameters': [
        {'name': 'pubkey', 'in': 'formData', 'required': False, 'type': 'string'},
        {'name': 'call_sign', 'in': 'formData', 'required': False, 'type': 'string'}],
    'responses': {
        '200': {'description': 'user details'},
        '404': {'description': 'user not found'}}}

CALLSIGNS = {
    'parameters': [
        {'name': 'call_sign_prefix', 'in': 'formData', 'required': False, 'type': 'string'}],
    'responses': {
        '200': {'description': 'registered call_signs'}}}

USER_INFOS = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'full_name', 'in': 'formData', 'type': 'string', 'required': False},
        {'name': 'phone_number', 'in': 'formData', 'type': 'string', 'required': False},
        {'name': 'address', 'in': 'formData', 'type': 'string', 'required': False}],
    'responses': {
        '201': {'description': 'user details set'},
        '400': {'description': 'invalid user info'},
        '404': {'description': 'user not found'}}}

PURCHASE_XLM = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'euro_cents', 'in': 'formData', 'type': 'integer', 'required': True},
        {'name': 'payment_currency', 'in': 'formData', 'type': 'string', 'required': True}],
    'responses': {
        '201': {'description': 'payment address generated'},
        '403': {'description': 'user not authorized'}}}

PURCHASE_BUL = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'euro_cents', 'in': 'formData', 'type': 'integer', 'required': True},
        {'name': 'payment_currency', 'in': 'formData', 'type': 'string', 'required': True}],
    'responses': {
        '201': {'description': 'payment address generated'},
        '403': {'description': 'user not authorized'}}}

REQUEST_VERIFICATION_CODE = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'}],
    'responses': {
        '200': {'description': 'code sent'},
        '403': {'description': 'not all user info was provided'}}}

VERIFY_CODE = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'verification_code', 'in': 'formData', 'type': 'string', 'required': True}],
    'responses': {
        '200': {'description': 'code verified'},
        '403': {'description': 'invalid or expired code'}}}

RATIO = {
    'parameters': [
        {'name': 'currency', 'in': 'formData', 'type': 'string', 'required': True, 'description': 'XLM'}],
    'responces': {
        '200': 'Euro cents price by one unit of specified currency'}
}

USERS = {'tags': ['debug'], 'responses': {'200': {'description': 'dict of users'}}}
