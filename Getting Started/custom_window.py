import operator

operators = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv
}
globalSettings = {}

def init(settings):
    global globalSettings
    globalSettings = settings
    return

def create(number_1,number_2):
    event = {}
    event['operator'] = globalSettings['operator']
    event['output_number'] = operators[event['operator']](number_1, number_2)
    return event

_espconfig_ = {
    "settings" : {
        "desc" : "",
        "expand_parms" : True,
        "process_blocks" : False,
        "encode_binary" : False
    },
    "inputVariables" : {
        "desc" : "",
        "fields" : [
            {
                "name": "number_1",
                "desc": "First number",
                "esp_type": "int32",
                "optional": False
            },
            {
                "name": "number_2",
                "desc": "Second number",
                "esp_type": "int32",
                "optional": False
            }
        ]
    },
    "outputVariables" : {
        "desc" : "",
        "fields" : [
            {
                "name": "operator",
                "desc": "Operator",
                "esp_type": "string"
            },
            {
                "name": "output_number",
                "desc": "Result",
                "esp_type": "double"
            }
        ]
    },
    "initialization" : {
        "desc" : "",
        "fields" : [
            {
                "name": "operator",
                "desc": "Mathematical operator",
                "default": "*",
                "input_type": "dropdown",
                "values": ["+","-","*","/"]
            }
        ]
    }
}
'''metadata start
{
    "name": "Mathematical Operations",
    "description": "Applies the selected mathematical operation to two input numbers.",
    "tags": [
        "example"
    ],
    "versionNotes": "First version"
}
metadata end'''