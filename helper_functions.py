import requests
import json,os
import logging
import pandas as pd

class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r

def get_bearer_token(client_id, client_secret):
    res = requests.post("https://auth.ocrolus.com/oauth/token", data={
        "grant_type": "client_credentials",
        "audience": "https://api.ocrolus.com/",
        "client_id": client_id,
        "client_secret": client_secret
    })
    auth = BearerAuth(res.json()["access_token"])
    return auth

def get_auth(filePath):
    with open(filePath, 'r') as oa_file:
        oa_json = json.loads(oa_file.read())
    return get_bearer_token(oa_json.get('clientId'), oa_json.get('clientSecret'))

def getDirectoryHierarchy(directory):
    hierarchy = []

    for root, dirs, files in os.walk(directory):
        subDir = {"directory": root, "files": []}
        hierarchy.append(subDir)
        for filename in files:
            subDir['files'].append(filename)

    df = pd.DataFrame(hierarchy)
    df = df.explode('files').reset_index()
    df = df.rename({'files': 'file'}, axis=1)
    #df['application_name'] = df['directory'].str.split(directory).str[1]
    return df


def getFileList(file_dir):
    flDF= getDirectoryHierarchy(file_dir)
    return flDF

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


def createBook(book_name,auth):
    # CREATE BOOK
    data = {'name': book_name,'book_class':'INSTANT'}

    try:
        cbr = json.loads(
            json.dumps(requests.post('https://api.ocrolus.com/v1/book/add', data=data, auth=auth).json()))

        logging.info(f'Create Book {book_name} Response: {json.dumps(cbr, indent=4)}')
        return cbr

        #book_uuid = cbr.get('response').get('uuid')
        #book_pk = cbr.get('response').get('pk')
        #return book_uuid
    except Exception as e:
        logging.error(f'{e}')
        return None

def configure_logging(cust_dir,file_name):
    logging.basicConfig(filename=cust_dir + '/'+file_name,
                        format='%(asctime)s %(levelname)s %(module)s:%(funcName)s():%(lineno)s %(message)s',
                        encoding='utf-8', level=logging.INFO)
    logging.info('Starting Processing')