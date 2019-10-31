import re
import requests
import json

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
    matches = [CN]
    for regex in REGEX_NAME:
        matches = re.findall(regex, frase)
        if matches:
            break
    return matches[0]

def get_med_name_nq(data, CN):
    frase = data['presentaciones'][0]['nombre']
    matches = [CN]
    for regex in REGEX_NAME:
        matches = re.findall(regex, frase)
        if matches:
            break
    return matches[0]

def get_num_pills(CN):
    data = get_json(CN)
    frase = data['presentaciones'][0]['nombre']
    matches = ['?']
    for regex in REGEX_PILLS:
        matches = re.findall(regex, frase)

        if matches:
            break
    return matches[0]

def get_num_pills_nq(data, CN):
    frase = data['presentaciones'][0]['nombre']
    matches = ['?']
    for regex in REGEX_PILLS:
        matches = re.findall(regex, frase)

        if matches:
            break
    return matches[0]



def get_info_about(CN):
    data = get_json(CN)
    estrink = 'El nombre del medicamento es '+ get_med_name_nq(data, CN) + '.\n'
    estrink += 'Contiene  dosis de '+ data['dosis'] + '.\n'
    estrink += 'Si desea mas informacion, puede consultar el prospecto en '+ data['docs'][1]['urlHtml']
    return estrink

if __name__ == '__main__':
    # CN = input('Introduzca el CN del medicamento ')
    CN = '664029'
    print('EL NOMBRE DEL MEDICAMENTO ES ' + get_med_name(CN) + '.\n')
    print('TIENE ' + get_num_pills(CN) + ' comprimidos')
    print(get_info_about(CN))
