import json
import re

import requests

REGEX_PILLS = ['(\d+) comprimido', '(\d+) cápsula']
REGEX_NAME = ['^(\w+ )']


def get_json(aux):
    CN = str.split(aux, ".")[0]
    try:
        r = requests.get(url="https://cima.aemps.es/cima/rest/medicamento?cn=" + CN)
        return r.json()
    except json.decoder.JSONDecodeError as ex:
        print("CN introduced does not exist")


def get_med_name(CN):
    data = get_json(CN)
    frase = data['presentaciones'][0]['nombre']
    matches = ''
    for regex in REGEX_NAME:
        matches = re.findall(regex, frase)
        if matches:
            break
    return matches[0]


def get_num_pills(CN):
    data = get_json(CN)
    frase = data['presentaciones'][0]['nombre']
    matches = ['']
    for regex in REGEX_PILLS:
        matches = re.findall(regex, frase)

        if matches:
            break
    return matches[0]


def get_info_about(CN):
    return json.dump(get_json(CN))


if __name__ == '__main__':
    CN = input('Introduzca el CN del medicamento ')
    print('EL NOMBRE DEL MEDICAMENTO ES ' + get_med_name(CN))
    print('TIENE ' + get_num_pills(CN) + ' comprimidos')
