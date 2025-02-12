import logging
import pandas as pd
import os,json
import requests,time
import datetime,threading
from helper_functions import *

def instantProcessImageFile(auth,book_uuid,local_file_path,flDF,index):
    # UPLOAD IMAGE
    with open(local_file_path, 'rb') as binary_file:
        binary_file_data = binary_file.read()
    files = {os.path.basename(local_file_path): binary_file_data}
    payload = {'book_uuid': book_uuid}

    uir = json.loads(json.dumps(
        requests.post('https://api.ocrolus.com/v1/book/upload/image', auth=auth, data=payload,
                      files=files).json()))
    flDF.loc[index,'image_group_pk'] = uir['response'].get('image_group_pk')
    logging.info(f'UploadImage {local_file_path} Response: {json.dumps(uir, indent=4)}')

    ## FINALIZE IMAGE GROUP
    payload = {'book_uuid': str(book_uuid)}
    close_image_group_response = json.loads(
        json.dumps(requests.post('https://api.ocrolus.com/v1/book/upload/image/done', auth=auth, data=payload).json()))
    logging.info(f'CloseImageGroup Response: {json.dumps(close_image_group_response, indent=4)}')
    flDF.loc[index,'mixed_doc_uuid'] = close_image_group_response.get('response').get('mixed_doc_uuid')

def instantProcessPDFFile(auth,book_uuid,local_file_path,flDF):
    print('f')
    try:
        ## UPLOAD PDF
        with open(local_file_path, 'rb') as binary_file:
            binary_file_data = binary_file.read()
        files = {os.path.basename(local_file_path): binary_file_data}
        payload = {'book_uuid': book_uuid}

        umdr = json.loads(json.dumps(
            requests.post('https://api.ocrolus.com/v1/book/upload/mixed', auth=auth, data=payload, files=files).json()))

        logging.info(f'MixedPDF {local_file_path} Response: {json.dumps(umdr, indent=4)}')
        return umdr
    except Exception as e:
        logging.error(f'{e}')

def upload_instant(prj_dir):
    file_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    #auth = get_auth('/Users/carsenault/Downloads/ocrolus_api_credentials_ARSENAULT_LCA_POC.json')
    auth = get_auth('/Users/carsenault/Downloads/ocrolus_api_credentials_ARSENAULT_LENDING_CLUB_INSTANT_POC.json')
    flDF = getFileList(file_dir).drop(columns='index').reset_index()
    #flDF = flDF[flDF.file == '466520225364.JPEG']
    fl_list = flDF.to_dict('records')

    for f in fl_list:
        try:
            ### CREATE BOOK
            book_name = f['file'].split('.')[0]
            response = createBook(book_name,auth)
            logging.info(f'{json.dumps(response)}')
            book_uuid = response.get('response').get('uuid')
            flDF.loc[f.get('index'),'create_book_response'] = json.dumps(response)
            flDF.loc[f.get('index'), 'book_uuid'] = book_uuid

            ### UPLOAD FILE
            if f.get('file').split('.')[-1] == 'PDF':
                umdr = instantProcessPDFFile(auth,book_uuid, f'{f.get("directory")}/{f.get("file")}',flDF)
                logging.info(f'{json.dumps(umdr)}')
                flDF.loc[f.get('index'),'mixed_doc_uuid'] = umdr.get('response').get('mixed_uploaded_docs')[0].get('uuid')
            else:
                instantProcessImageFile(auth, book_uuid, f'{f.get("directory")}/{f.get("file")}',flDF,f.get('index'))
        except Exception as e:
            logging.error(f'{f["file"]} {e}')
            print(f'{f["file"]} -- {e}')
        flDF.to_csv(f'{prj_dir}/instant_upload_result.csv')
        time.sleep(2)

    flDF.to_csv(f'{prj_dir}/instant_upload_result.csv')
    print('Done')
