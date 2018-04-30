"""Swagger specifications of Identity Server."""

CONFIG = {
    'title': 'PaKeT identity API',
    'uiversion': 2,
    'specs_route': '/',
    'specs': [{
        'endpoint': '/',
        'route': '/apispec.json',
        'rule_filter': lambda rule: True,  # all in
        'model_filter': lambda tag: True,  # all in
    }],
    'info': {
        'title': 'The PaKeT identity server API',
        'contact': {
            'name': 'The PaKeT Project',
            'email': 'israel@paket.global',
            'url': 'https://identity.paket.global',
        },
        'version': 2,
        'license': {
            'name': 'GNU GPL 3.0',
            'url': 'http://www.gnu.org/licenses/'
        },
        'description': '''
Web API Server for The PaKeT Project

What is this?
=============
This page is used as both documentation of our server API and as a sandbox to
test interaction with it. You can use this page to call the RESTful API while
specifying any required or optional parameter. The page also presents curl
commands that can be used to call the server.

Our Server
==========
We run a centralized server that can be used to interact with PaKeT's bottom
layers.  Since Layer one is completely implemented on top of the Stellar
network, it can be interacted with directly in a fully decentralized fashion.
We created this server only as a gateway to the bottom layers to simplify the interaction with them.

Another aspect of the server is to interact with our user information.
Ultimately, we will use decentralize user information solutions, such as Civic,
but right now we are keeping user for both KYC and app usage. Please review our
roadmap to see our plans for decentralizing the user data.

Security
========
Our calls are split into the following security levels:
 - Debug functions: no authentication allowed. Available only in debug mode.
 - Anonymous functions: no authentication allowed.
 - Authenticated functions: require asymmetric key authentication. Not tested in debug mode.
    - The 'Pubkey' header will contain the user's pubkey. In debug mode this can be substituted with his paket_user.
    - The 'Fingerprint' header is constructed from the comma separated
      concatenation of the called URI, all the arguments (as key=value), and an
      ever increasing nonce (recommended to use Unix time in milliseconds).
    - The 'Signature' header will contain the signature of the key specified in
      the 'Pubkey' header on the fingerprint specified in the 'Fingerprint'
      header, encoded to string as Base64.

Walkthrough
===========
You can follow the following steps one by one.
They are ordered in a way that demonstrates the main functionality of the API.

Register a User
---------------
First, register a new user:
* register_user: if you are in debug mode make sure to use the value 'debug' as the Pubkey header. In such a case,
a keypair will be generated and held on your behalf by the system.
Your call should return with status code 201 and a JSON with the new user's details.
On the debug environment this will include the generated secret seed of the keypair.
* recover_user: use the pubkey from the previous step.
Your call should return with a status of 200 and all the details of the user
(including the secret seed on the debug environment, as above).

Fund Wallet
-----------
Verify a zero balance, and than fund the account.
* get_bul_account: use the same pubkey as before.
Your call should return a status of 200 and include the newly created user's balance in BULs (should be 0),
a list of the signers on the account (should be only the user's pubkey),
a list of thresholds (should all be 0) and a sequence number (should be a large integer).
* send_buls: In a production environment, you should use the keypair of a BUL holding account you control for the
headers. On the debug environment, you should use the value 'ISSUER', which has access to an unlimited supply of BULs,
for the Pubkey header. Use the pubkey from before as value for the to_pubkey
field, and send yourself 222 BULs.  Your call should return with a status of
201, and include the transaction details.  Of these, copy the value of
['transaction']['hash'] and use the form on the following page to fetch and
examine it:
https://www.stellar.org/laboratory/#explorer?resource=transactions&endpoint=single&network=test
(specifically, if you click the envelope_xdr that you will receive it will open
in the XDR viewer where you can view the payment operation, and if you click
the result_xdr you can check that the payment operation has succeeded).
* get_bul_account: use this call again, with the new user's pubkey,
to ensure that your balance reflects the latest transaction.
Your call should return a status of 200 with the same details as the previous call,
excepting that the balance should now be 222.

Create (Launch) a Package
-------------------------
* launch_package: use the new user's pubkey in the header.
Use the recipient's pubkey for the recipient_pubkey field and the courier's pubkey for the courier_pubkey field
(in the debug environment you can use the strings 'RECIPIENT' and 'COURIER' for the built-in pre-funded accounts).
Set the deadline for the delivery in Unix time (https://en.wikipedia.org/wiki/Unix_time),
with 22 BULs as payment_buls and 50 BULs as collateral_buls. The call will
return an escrow_address, which also serves as the package's ID, a timelocked
refund_transaction that can only be submitted once the deadline expires, and a
payment_transaction which has to be signed by the recipient to be valid.
* package: get the package's details. The custodian should now be the launcher.
Note that in debug mode the 'events' array is filled with random mock data.
* get_bul_account: use the escrow_address. Balance should be 0, thresholds
should be 1, 2, and 3, and the signers array should contain exaxtly four
values: the escrow_address pubkey with a weight of 0, the recipient pubkey with
a weight of 1, the payment_transaction hash with a weight of 1, and the
refund_transaction hash with a weight of 2.
* get_bul_account: check and make note of the balances of launcher, courier, and recipient.
* send_buls: as the launcher, deposit 22 BULs into the escrow_address as promised payment.
* get_bul_account: use the launcher's pubkey. Should now be 22 BULs poorer.
* send_buls: as the courier, deposit 50 BULs into the escrow_address as committed collateral.
* get_bul_account: use the courier's pubkey. Should now be 50 BULs poorer.
* accept_package: accept the package as the courier, with the escrow_address as paket_id.
* package: get the package's details. The custodian should now be the courier.
* accept_package: accept the package as the recipient, with the escrow_address
as paket_id and the payment_transaction from launch_package as
payment_transaction.
* package: get the package's details. The custodian should now be the recipient.
* get_bul_account: use the courier's pubkey. Should now be 72 BULs richer than
last time (22 awarded payment + 50 returned collateral).

Undocumented for Now
====================
debug functions
price
prepare_send_buls
submit_transaction

The API
=======
        '''
    }
}

TEST = {
    "parameters": [
        {
            "name": "palette",
            "in": "path",
            "type": "string",
            "enum": [
                "all",
                "rgb",
                "cmyk"
                ],
            "required": "true",
            "default": "all"
        }
    ],
    "definitions": {
        "Palette": {
            "type": "object",
            "properties": {
                "palette_name": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Color"
                    }
                }
            }
        },
        "Color": {"type": "string"}
    },
    "responses": {
        "200": {
            "description": "A list of colors (may be filtered by palette)",
            "schema": {
                "$ref": "#/definitions/Palette"},
            "examples": {
                "rgb": [
                    "red",
                    "green",
                    "blue"
                ]
            }
        }
    }
}
