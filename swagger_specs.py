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
What does this do?

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
                'NOT NEEDED YET http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': 'NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
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
            'description': 'User created',
            'examples': {
            }
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
                'NOT NEEDED YET http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': 'NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
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
            'examples': {
            }
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
                'NOT NEEDED YET http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': 'NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
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
                'NOT NEEDED YET http://localhost:5000/v1/send_buls,to_pubkey=pubkey,amount_buls=amount,1521650747',
            'schema': {
                'type': 'string',
                'format': 'string'
            }
        },
        {
            'name': 'Signature',
            'in': 'header',
            'default': 'NOT NEEDED YET 0xa7d77cf679a2456325bbba3b92d994f5987b68c147bad18e24e6b66f5dc',
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
