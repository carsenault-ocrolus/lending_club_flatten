import pandas as pd
import os,json
import requests
import logging
import datetime,threading
from helper_functions import *
from instant_processing import *
from optimaFlatten import *
from instantFlatten import *

### LOGGING CONFIG
prj_dir = '/Users/carsenault/CustPrj/lendingclub/'
configure_logging(prj_dir,'logFile.txt')

## Optima Thread Lock
lock = threading.Lock()

def processImageFile(auth,local_file_path):
    url = 'https://apika.ocrolus.com/ml/v2/instant/images'
    #headers={'Content-Type':'application/jpeg'}
    files = {"files": (local_file_path, open(local_file_path, "rb"), f'image/{local_file_path.split(".")[-1].lower()}')}
    headers = {"accept": "application/json"}

    start_time = datetime.now()
    uploadResponse = requests.post(url, auth=auth, files=files, headers=headers)
    end_time = datetime.now()
    with open('/Users/carsenault/CustPrj/lendingclub/outbound/' + os.path.basename(local_file_path).split('.')[0]+'.json', 'w') as outFile:
        outFile.write(json.dumps(uploadResponse.json(), indent=4))
    return start_time,end_time
    pass

def processPdfFile(auth,local_file_path):
    url = 'https://apika.ocrolus.com/ml/v2/instant'

    with open(local_file_path, 'rb') as binary_file:
        binary_file_data = binary_file.read()
    files = {os.path.basename(local_file_path): binary_file_data}
    headers = {
        "accept": "application/json",
        "content-type": "application/pdf"
    }

    start_time = datetime.now()
    uploadResponse = requests.post(url, headers=headers,auth=auth, files=files)
    end_time = datetime.now()
    with open('/Users/carsenault/CustPrj/lendingclub/optima_outbound/' + os.path.basename(local_file_path).split('.')[0]+'.json', 'w') as outFile:
        outFile.write(json.dumps(uploadResponse.json(), indent=4))
    return start_time,end_time
    pass

def write_optima_thread(threadname,bl_list,auth,class_dir,flDF):
    for book in bl_list:
        try:
            if book.get('file').split('.')[-1] == 'PDF':
                start_time, end_time = processPdfFile(auth, f'{book.get("directory")}/{book.get("file")}')
            else:
                start_time, end_time = processImageFile(auth, f'{book.get("directory")}/{book.get("file")}')
            with lock:
                flDF.loc[book.get('index'), 'start_time'] = start_time
                flDF.loc[book.get('index'), 'end_time'] = end_time
                #flDF.loc[book.get('index'), 'jsonResponse'] = json.dumps(jsonResponse)
        except Exception as e:
            print(f'{e}')
        pass

def writeOptima(num_threads,file_list,auth,out_dir,flDF):
    threads = list()
    threadNum = 0

    for y in split(file_list, num_threads):
        x = threading.Thread(target=write_optima_thread, args=(threadNum, y,auth,out_dir,flDF))
        threads.append(x)
        x.start()
        threadNum += 1
    for index, thread in enumerate(threads):
        thread.join()


def main(fileDir):
    #auth = get_bearer_token('XHRELKE1tIQgyCkzWjtHQoqCG2j9N8oh','_8nMrW5idKAr01AjnYCZWl6jVRKw_WWn6r95QZg7N51gO2Hi2FMdKcXhwU8YIetC')
    #auth = get_bearer_token('wT5Map1zumU3zQgABB4K2yYzn1nmNdc3','n4POoKzw5r6iRaNTpjeRQAJNPtKvc0SmTRgMTjbNTrorWypkWxq7_bSalpVgyjF6')
    auth = get_auth('/Users/carsenault/Downloads/ocrolus_api_credentials_ARSENAULT_LENDING_CLUB_INSTANT_POC.json')
    flDF = getFileList(fileDir).drop(columns='index').reset_index()

    #### ONE FILE ONLY
    flDF = flDF[flDF.file == '466518775285.PDF'].copy()
    fl_list = flDF.to_dict('records')
    flDF['jsonResponse'] = ''

    writeOptima(8,fl_list,auth,'/Users/carsenault/CustPrj/lendingclub/optima_outbound/',flDF)

    flDF.to_csv(f'{fileDir}/flDF_{datetime.now()}.csv')
    print(f'f')

def add_form_type(form_list,form_type):
    if form_type in form_list:
        form_list[form_type] = form_list.get(form_type) + 1
    else:
        form_list[form_type] = 1

def analyze_classification(output_dir):
    all_entries = os.listdir(output_dir)
    files = [entry for entry in all_entries if os.path.isfile(os.path.join(output_dir, entry))]
    form_dict={}
    form_list=[]

    for x in files:
        try:
            with open(f'{output_dir}/{x}','r') as opt_file:
                opt_json = json.load(opt_file)
            if type(opt_json) == list:
                for form in opt_json:
                    form_type = form.get('form_type').get('name')
                    add_form_type(form_dict,form_type)
                    print(f'{form_type}')
            else:
                print(f'{json.dumps(opt_json)}')
        except Exception as e:
                pass
    df = pd.DataFrame(list(form_dict.items()), columns=['form_type', 'Count'])
    df.to_csv(f'{output_dir}/form_list.csv')
    print('f')

def analyze_capture(output_dir):
    all_entries = os.listdir(output_dir)
    files = [entry for entry in all_entries if os.path.isfile(os.path.join(output_dir, entry))]
    form_list = []

    for x in files:
        try:
            with open(f'{output_dir}/{x}','r') as opt_file:
                opt_json = json.load(opt_file)
            if type(opt_json) == list:
                for form in opt_json:
                    form_dict={"file_name":x,"page_indexes":str(form.get('page_indexes')),'field_count':len(form.get('fields')),'form_type':form.get('form_type').get('name')}
                    form_list.append(form_dict)
            else:
                print(f'{json.dumps(opt_json)}')
        except Exception as e:
                pass
    df = pd.DataFrame.from_records(form_list)
    df.to_csv(f'{output_dir}/field_count.csv')
    print('Done Capture Anaylsis')

def count_string_fields(data):
    if isinstance(data, str):
        return 1
    elif isinstance(data, dict):
        return sum(count_string_fields(value) for value in data.values())
    elif isinstance(data, list):
        return sum(count_string_fields(item) for item in data)
    else:
        return 0



def analyze_instant_capture(output_dir):
    #all_entries = os.listdir(output_dir)
    #files = [entry for entry in all_entries if os.path.isfile(os.path.join(output_dir, entry))]
    files = [os.path.join(dp, f) for dp, dn, fn in os.walk(os.path.expanduser(output_dir)) for f in fn]

    form_list = []

    for x in files:
        try:
            with open(x,'r') as capt_file:
                capt_json = json.load(capt_file)

                for form in capt_json.get('response').get('forms'):
                    #field_count= len(form.get('raw_fields'))
                    raw_field_count = len(form.get('raw_fields'))
                    field_count=0
                    for field in form.get('raw_fields'):
                        if form.get('raw_fields').get(field).get('is_empty') == False:
                            field_count+=1
                    form_type = form.get('form_type')
                    field_dict={'file_name':x,'field_count':field_count,'raw_field_count':raw_field_count,'form_type':form_type}
                    form_list.append(field_dict)
        except Exception as e:
            print(f'{x} {json.dumps(capt_json)}')
            logging.error(f'{x} {json.dumps(capt_json)}')


    df = pd.DataFrame.from_records(form_list)
    df.to_csv(f'{output_dir}/instant_field_count.csv')
    print('Done Instant Capture Anaylsis')



if __name__ == '__main__':
    #analyze_classification('/Users/carsenault/CustPrj/lendingclub/outbound/')
    #analyze_capture('/Users/carsenault/CustPrj/lendingclub/optima_outbound/')
    #main('/Users/carsenault/CustPrj/lendingclub/inbound/Ocrolus Confidential and Private Data/')
    #upload_instant('/Users/carsenault/CustPrj/lendingclub/')
    #analyze_instant_capture('/Users/carsenault/CustPrj/lendingclub/outbound/formData')


    ### OPTIMA ETL
    #optimaClassificationFlatten(prj_dir)
    #optimaCaptureFlattenLCMapping(prj_dir)
    #optimaCaptureFlattenNoMapping(prj_dir)

    ## INSTANT ETL
    #instantClassificationFlatten(prj_dir)
    instantCaptureFlattenLCMapping(prj_dir)
    #instantCaptureFlattenNoMapping(prj_dir)