"""Swagger specifications of Identity Server."""
VERSION = 1
CONFIG = {
    'title': 'PaKeT identity API',
    'uiversion': 2,
    'specs_route': '/',
    'specs': [{
        'endpoint': '/',
        'route': '/apispec.json',
    }],
    'info': {
        'title': 'The PaKeT Identity Server API',
        'version': VERSION,
        'contact': {
            'name': 'The PaKeT Project',
            'email': 'israel@paket.global',
            'url': 'https://identity.paket.global',
        },
        'license': {
            'name': 'GNU GPL 3.0',
            'url': 'http://www.gnu.org/licenses/'
        },
        'description': '''

The Identity server is responsible for registering users. 
A user registration is simply a connection between a single BUL account and the details of it's holder.
The Identity Server also performs KYC/AML checks on registered users.

BULs Account
--
A BULs account is a Stellar account that trusts PaKeT's BUL token.

User Details
--  
Details of the person holding the account, including: 
 - full_name 
 - phone_number 
 - address
 - paket_user
  
These details are added at registration time.
Details on the KYC status of the user:
- KYC status - based on the servers tests
- Funding limit - the maximal amount that the user is allowed to purchase. This is dependant on the user's KYC status.

Authorization
--
The data is available only to the user who registered, and anyone he authorize access to. 
A normal process is for a user to authorize himself, the PaKeT server [and the funding server??].  


The API
=======



        '''
    }
}

USER_POST = {
    'parameters': [
        {
            'name': 'Pubkey',
            'default': 'GBQOQ4LJC5YNIAYIC3WPNGLPHNBKAP6UJTLC3KGXI6QLZSFGJSASEOC4',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Fingerprint',
            'in': 'header',
            'default':
                'http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': '0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
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

USER_GET = {
    'parameters': [
        {
            'name': 'Pubkey',
            'default': 'GBQOQ4LJC5YNIAYIC3WPNGLPHNBKAP6UJTLC3KGXI6QLZSFGJSASEOC4',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Fingerprint',
            'in': 'header',
            'default':
                'http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': '0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'queried_pubkey',
            'in': 'query',
            'type': 'string',
            'required': False,
        }
    ],
    'responses': {
        '200': {
            'description': 'User retrieved',
        },
        '403': {
            'description': 'Forbidden. Requesting user is not authorized with information about requested user.',
        },
        '404': {
            'description': 'Not Found. Requested user is not registered.',
        }

    }
}

AUTHORIZE = {
    'parameters': [
        {
            'name': 'Pubkey',
            'default': 'GBQOQ4LJC5YNIAYIC3WPNGLPHNBKAP6UJTLC3KGXI6QLZSFGJSASEOC4',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Fingerprint',
            'in': 'header',
            'default':
                'http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': '0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'authorized_pubkey',
            'in': 'formData',
            'type': 'string',
            'required': True,
        },
    ],
    'responses': {
        '201': {
            'description': 'Authorization added',
            'examples': {
            }
        }
    }
}

UNAUTHORIZE = {
    'parameters': [
        {
            'name': 'Pubkey',
            'default': 'GBQOQ4LJC5YNIAYIC3WPNGLPHNBKAP6UJTLC3KGXI6QLZSFGJSASEOC4',
            'in': 'header',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Fingerprint',
            'in': 'header',
            'default':
                'http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': '0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'authorized_pubkey',
            'in': 'formData',
            'type': 'string',
            'required': True,
        },
    ],
    'responses': {
        '201': {
            'description': 'Authorization revoked',
            'examples': {
            }
        }
    }
}
