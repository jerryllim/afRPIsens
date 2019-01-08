import json

settings_json = json.dumps([
    {'type': 'title',
     'title': 'General'},
    {'type': 'options',
     'title': 'Number of employees',
     'desc': 'Set number of employees',
     'key': 'num_operators',
     'section': "General",
     'options': ['1', '2', '3']},
    {'type': 'string',
     'title': 'Waste1 units',
     'desc': 'Units available for Waste1 (delimit with ",")',
     'key': 'waste1_units',
     'section': "General"},
    {'type': 'string',
     'title': 'Waste2 units',
     'desc': 'Units available for Waste2 (delimit with ",")',
     'key': 'waste2_units',
     'section': "General"},
    {'type': 'button',
     'title': 'Pin Configurations',
     'desc': 'To configure pins',
     'key': 'pin_config',
     'section': "General"},
    {'type': 'title',
     'title': 'Network'},
    {'type': 'string',
     'title': 'IP Address',
     'desc': 'Server IP Address',
     'key': 'ip_add',
     'section': "Network"},
    {'type': 'numeric',
     'title': 'Port',
     'desc': 'Server Port',
     'key': 'port',
     'section': "Network"}
])
