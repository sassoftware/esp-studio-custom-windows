def create(number_1, number_2):
    event = {}
    event['output_number'] = number_1 * number_2
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
                "optional": False
            },
            {
                "name": "number_2",
                "desc": "Second number",
                "optional": False
            }
        ]
    },
    "outputVariables" : {
        "desc" : "",
        "fields" : [
            {
                "name": "output_number",
                "desc": "Result"
            }
        ]
    }
}
'''metadata start
{
    "name": "Multiplication",
    "description": "This custom window multiplies two numbers. ",
    "tags": [
        "example"
    ],
    "versionNotes": "First version"
}
metadata end'''
