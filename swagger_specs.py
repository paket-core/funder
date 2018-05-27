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
BULs used to launcha packages.

This requires user registration, so we can perform KYC/AML checks.

A secondary function of the Funding server is an internal identity server,
which resolves a unique call sign to a public key and Stellar address.

Security
========
Our calls are split into the following security levels:
 - Debug functions: require no authentication, available only in debug mode.
 - Anonymous functions: require no authentication.
 - Authenticated functions: require asymmetric key authentication. Not tested
   in debug mode.
    - The 'Pubkey' header will contain the user's pubkey.
    - The 'Fingerprint' header is constructed from the comma separated
      concatenation of the called URI, all the arguments (as key=value), and an
      ever increasing nonce (recommended to use Unix time in milliseconds).
    - The 'Signature' header will contain the signature of the key specified in
      the 'Pubkey' header on the fingerprint specified in the 'Fingerprint'
      header, encoded to Base64 ASCII.

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

ADD_USER = {
    'parameters': [
        {'name': 'Pubkey', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Fingerprint', 'in': 'header', 'required': True, 'type': 'string'},
        {'name': 'Signature', 'in': 'header', 'required': True, 'type': 'string'},
        {
            'name': 'full_name',
            'in': 'formData',
            'type': 'string',
            'required': True,
        },
        {
            'name': 'phone_number',
            'in': 'formData',
            'type': 'string',
            'required': True,
        },
        {
            'name': 'address',
            'in': 'formData',
            'type': 'string',
            'required': True,
        },
        {
            'name': 'paket_user',
            'in': 'formData',
            'type': 'string',
            'required': True,
        },
    ],
    'responses': {
        '201': {
            'description': 'User created'
        },
        '400': {
            'description': 'Bad Request: pubkey is not related to a valid account'
        }
    }
}
