{
    'name': 'Uploading Shipping Report',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'summary': '...',
    'sequence': '1',
    'author': 'Martynas Minskis',
    'depends': ['sale'],
    'demo': [],
    'data': [

        # Sequence: security, data, wizards, views
        'views/shipping_report_upload.xml',
    ],
    'demo': [],
    'qweb': [],

    'installable': True,
    'application': True,
    'auto_install': False,
    #     'licence': 'OPL-1',
}