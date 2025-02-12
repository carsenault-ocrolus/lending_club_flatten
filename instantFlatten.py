import logging

import pandas as pd

from helper_functions import *
from datetime import datetime
from jsonpath_ng import jsonpath, parse

def getDetectInfo(form,detect_json):
    fraudulent = 'NA'
    score = None
    form_uuid = form.get('form_uuid')
    form_type = form.get('form_type').get('name')

    if form_type == 'BANK_ACCOUNT':
        for doc in detect_json.get('doc_analysis'):
            for fa in doc.get('form_analysis'):
                if fa.get('form_type') == 'BANK_STATEMENT':
                    score = fa.get('form_authenticity').get('score')
                    fraudulent = 'TRUE' if int(score) < 80 else 'FALSE'
        return fraudulent, score

    for doc in detect_json.get('doc_analysis'):
        for fa in doc.get('form_analysis'):
            if (form_type == fa.get('form_type')) and (form_uuid == fa.get('form_uuid')):
                score = fa.get('form_authenticity').get('score')
                fraudulent = 'TRUE' if int(score)<80 else 'FALSE'
    return fraudulent,score

def get_passes_validation(form,form_json):
    passes_validation = False
    form_uuid = form.get('form_uuid')
    form_type = form.get('form_type').get('name')

    for f in form_json.get('response').get('forms'):
        if f.get('uuid') == form_uuid:
            passes_validation = f.get('passes_validation')

    return passes_validation ## TRUE OR FALSE



def instantClassificationFlatten(prj_dir):
    inbound_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    outbound_dir = f'{prj_dir}/outbound/classification/'
    detect_dir = f'{prj_dir}/outbound/Detect/'
    form_dir = f'{prj_dir}/outbound/formData/'

    df = getFileList(inbound_dir)
    class_list = []

    for index, row in df.iterrows():
        instant_json_file = f"{row.file.split('.')[0]}.json"

        with open(f'{outbound_dir}/{instant_json_file}', 'r') as inst_file:
            inst_json = json.load(inst_file)

        with open(f'{detect_dir}/{instant_json_file}', 'r') as detect_file:
            detect_json = json.load(detect_file)

        with open(f'{form_dir}/{instant_json_file}', 'r') as form_file:
            form_json = json.load(form_file)

        instant_timing_df = pd.read_csv(f'{prj_dir}/analysis/instant_process_time.csv',dtype=str)

        # LOOP THROUGH FORMS IN JSON
        for form in inst_json.get('response').get('forms'):
            form_dict={}
            form_dict['file_name'] = row.file
            form_dict['page_indexes'] = form.get('upload_details').get('mixed_doc_page_indexes')
            form_dict['doc_type'] = None
            form_dict['doc_type_c_score'] = None
            form_dict['sub_type'] = form.get('form_type').get('name')
            form_dict['sub_type_c_score'] = form.get('upload_details').get('confidence')
            for key in ['legible_quality','quality_score','quality_c_score']:
                form_dict[key] = None

            form_dict['fraudulent'],  form_dict['trust_score'] = getDetectInfo(form,detect_json)

            for key in ['completeness', 'completeness_score', 'completeness_c_score','correctness', 'correctness_c_score']:
                form_dict[key] = None

            book_name = row.file.split('.')[0]
            # Parse the string into a datetime object
            upload_row = instant_timing_df[instant_timing_df.book_name == book_name]

            if len(upload_row)==0:
                upload_row=None
            else:
                upload_row = upload_row.iloc[0]

            time_format = '%Y-%m-%d %H:%M:%S.%f'
            #start_time = datetime.strptime(upload_row.start_time, time_format)
            #end_time = datetime.strptime(upload_row.end_time, time_format)
            #diff_time = end_time-start_time
            #start_time = start_time.isoformat()
            #end_time = end_time.isoformat()
            if upload_row is None:
                start_time =  0
                end_time = 0
                diff_time = 0
            else:
                start_time = datetime.strptime(upload_row.mixed_doc_created, time_format)
                end_time = datetime.strptime(upload_row.mixed_doc_verified, time_format)
                diff_time = end_time - start_time
                diff_time = f'{diff_time.seconds}.{diff_time.microseconds}'
            form_dict['quality_checks_start'] = start_time
            form_dict['quality_checks_end'] = end_time
            form_dict['quality_checks_duration'] = diff_time
            form_dict['classification_start'] = start_time
            form_dict['classification_end'] = end_time
            form_dict['classification_duration'] = diff_time
            form_dict['validation_start'] = start_time
            form_dict['validation_end'] = end_time
            form_dict['validation_duration'] = diff_time
            form_dict['entity_extraction_start'] = start_time
            form_dict['entity_extraction_end'] = end_time
            form_dict['entity_extraction_duration'] = diff_time
            form_dict['end_to_end_start'] = start_time
            form_dict['end_to_end_end'] = end_time
            form_dict['end_to_end_duration'] = diff_time
            form_dict['doc_page_count'] = len(form.get('upload_details').get('mixed_doc_page_indexes'))
            form_dict['doc_status'] = 'SUCCESS'
            form_dict['vendor_product_id'] = 'INSTANT'
            form_dict['vendor_product_version'] = '1.0'
            form_dict['vendor_id'] = 'OCROLUS'
            form_dict['form_uuid'] = form.get('form_uuid')
            form_dict['passes_validation'] = get_passes_validation(form,form_json)
            class_list.append(form_dict)
    classDf = pd.DataFrame.from_records(class_list)
    classDf.to_csv(f'{outbound_dir}/Ocrolus_Instant_Doc_Level.csv',index=False)





def extract_field_from_json(json_data, jsonpath_str):
    """
    Extracts a field from a JSON object using a JSONPath string.

    :param json_data: The JSON object (as a dictionary) to search.
    :param jsonpath_str: The JSONPath string to use for extraction.
    :return: A list of matching values, or an empty list if no match is found.
    """
    try:
        # Parse the JSONPath string
        jsonpath_expr = parse(jsonpath_str)

        # Find matches in the JSON data
        matches = [match.value for match in jsonpath_expr.find(json_data)]

        return matches
    except Exception as e:
        print(f"Error: {e}")
        return []

def appendPSData(prj_dir,row,capt_list,capt_list_full, capt_map):
    app_number = row.file.split('.')[0]
    file_path = f'{prj_dir}/outbound/Paystub/{app_number}.json'
    if not os.path.exists(file_path):
        return

    capt_map = capt_map[capt_map.ocrolus_form=='PAYSTUB']

    with open(file_path, 'r') as paystub_file:
        paystub_json = json.load(paystub_file)

    for paystub in paystub_json.get('response'):
        for index, keyrow in capt_map.iterrows():
            if keyrow.ocrolus_key == '$.net_pay.totals.current_pay.amount':
                if extract_field_from_json(paystub, keyrow.ocrolus_key)[0] is None:
                    distDetails = extract_field_from_json(paystub,'$.net_pay.distribution_details')

                    distAmount = 0
                    distFound = False
                    for dist in distDetails[0]:
                        val = dist.get('current_pay').get('amount')
                        if val is None:
                            continue
                        distAmount += float(val)
                        distFound = True

                    if not distFound:
                        distAmount = None

                    form_dict = {}
                    form_dict['Vendor_JSON_field_name'] = keyrow.ocrolus_key
                    form_dict['file_name'] = row.file
                    form_dict['ocrolus_doc_type'] = 'PAYSTUB'
                    form_dict['doc_type'] = keyrow.doc_type
                    form_dict['sub_type'] = keyrow.sub_type
                    form_dict['section_name'] = keyrow.section_name
                    form_dict['attribute_key'] = keyrow.attribute_key

                    ### OCROLUS VALUES
                    #form_dict['attribute_value (raw)'] = extract_field_from_json(paystub, '$.net_pay.distribution_details[{iter}].current_pay.amount')[0]
                    form_dict['attribute_value (raw)'] = distAmount
                    form_dict['attribute_value (normalized)'] = None
                    form_dict['attribute_value_c_score'] = None
                    form_dict['attribute_value_precision_score (optional)'] = None

                    ## LAST 3 COLUMNS. VENDOR INFORMATION
                    form_dict['vendor_product_id'] = 'INSTANT'
                    form_dict['vendor_product_version'] = '1.0'
                    form_dict['vendor_id'] = 'OCROLUS'
                    form_dict['form_uuid'] = paystub.get('uuid')

                    capt_list.append(form_dict)
                    capt_list_full.append(form_dict)

                    continue
                else:
                    print(f'{row.file} {keyrow.ocrolus_key} {extract_field_from_json(paystub, keyrow.ocrolus_key)}')

                    form_dict = {}
                    form_dict['Vendor_JSON_field_name'] = keyrow.ocrolus_key
                    form_dict['file_name'] = row.file
                    form_dict['ocrolus_doc_type'] = 'PAYSTUB'
                    form_dict['doc_type'] = keyrow.doc_type
                    form_dict['sub_type'] = keyrow.sub_type
                    form_dict['section_name'] = keyrow.section_name
                    form_dict['attribute_key'] = keyrow.attribute_key

                    ### OCROLUS VALUES
                    form_dict['attribute_value (raw)'] = extract_field_from_json(paystub, keyrow.ocrolus_key)[0]
                    form_dict['attribute_value (normalized)'] = None
                    form_dict['attribute_value_c_score'] = None
                    form_dict['attribute_value_precision_score (optional)'] = None

                    ## LAST 3 COLUMNS. VENDOR INFORMATION
                    form_dict['vendor_product_id'] = 'INSTANT'
                    form_dict['vendor_product_version'] = '1.0'
                    form_dict['vendor_id'] = 'OCROLUS'
                    form_dict['form_uuid'] = paystub.get('uuid')

                    capt_list.append(form_dict)
                    capt_list_full.append(form_dict)
                    continue

            ### ALL OTHER FIELDS
            if len(extract_field_from_json(paystub,keyrow.ocrolus_key)) == 0:
                print(f'{row.file} {keyrow.ocrolus_key}  EMPTY')
            else:
                print(f'{row.file} {keyrow.ocrolus_key} {extract_field_from_json(paystub,keyrow.ocrolus_key)}')

                form_dict = {}
                form_dict['Vendor_JSON_field_name'] = keyrow.ocrolus_key
                form_dict['file_name'] = row.file
                form_dict['ocrolus_doc_type'] = 'PAYSTUB'
                form_dict['doc_type'] = keyrow.doc_type
                form_dict['sub_type'] = keyrow.sub_type
                form_dict['section_name'] = keyrow.section_name
                form_dict['attribute_key'] = keyrow.attribute_key

                ### OCROLUS VALUES
                form_dict['attribute_value (raw)'] = extract_field_from_json(paystub,keyrow.ocrolus_key)[0]
                form_dict['attribute_value (normalized)'] = None
                form_dict['attribute_value_c_score'] = None
                form_dict['attribute_value_precision_score (optional)'] = None

                ## LAST 3 COLUMNS. VENDOR INFORMATION
                form_dict['vendor_product_id'] = 'INSTANT'
                form_dict['vendor_product_version'] = '1.0'
                form_dict['vendor_id'] = 'OCROLUS'
                form_dict['form_uuid'] = paystub.get('uuid')

                capt_list.append(form_dict)
                capt_list_full.append(form_dict)


def appendPSDataOrig(prj_dir,row,capt_list,capt_list_full, capt_map):
    app_number = row.file.split('.')[0]
    file_path = f'{prj_dir}/outbound/Paystub/{app_number}.json'
    if not os.path.exists(file_path):
        return

    capt_map = capt_map[capt_map.ocrolus_form=='PAYSTUB']

    with open(file_path, 'r') as paystub_file:
        paystub_json = json.load(paystub_file)

    for paystub in paystub_json.get('response'):
        for index, keyrow in capt_map.iterrows():
            ### ALL FIELDS
            if len(extract_field_from_json(paystub,keyrow.ocrolus_key)) == 0:
                print(f'{row.file} {keyrow.ocrolus_key}  EMPTY')
            else:
                print(f'{row.file} {keyrow.ocrolus_key} {extract_field_from_json(paystub,keyrow.ocrolus_key)}')

                form_dict = {}
                form_dict['Vendor_JSON_field_name'] = keyrow.ocrolus_key
                form_dict['file_name'] = row.file
                form_dict['ocrolus_doc_type'] = 'PAYSTUB'
                form_dict['doc_type'] = keyrow.doc_type
                form_dict['sub_type'] = keyrow.sub_type
                form_dict['section_name'] = keyrow.section_name
                form_dict['attribute_key'] = keyrow.attribute_key

                ### OCROLUS VALUES
                form_dict['attribute_value (raw)'] = extract_field_from_json(paystub,keyrow.ocrolus_key)[0]
                form_dict['attribute_value (normalized)'] = None
                form_dict['attribute_value_c_score'] = None
                form_dict['attribute_value_precision_score (optional)'] = None

                ## LAST 3 COLUMNS. VENDOR INFORMATION
                form_dict['vendor_product_id'] = 'INSTANT'
                form_dict['vendor_product_version'] = '1.0'
                form_dict['vendor_id'] = 'OCROLUS'
                form_dict['form_uuid'] = paystub.get('uuid')

                capt_list.append(form_dict)
                capt_list_full.append(form_dict)




def appendBSData(prj_dir,row,capt_list,capt_list_full, capt_map):
    app_number = row.file.split('.')[0]
    file_path = f'{prj_dir}/outbound/OcrolusAnalytics/{app_number}/analyticsV2.json'
    if not os.path.exists(file_path):
        return

    with open(file_path, 'r') as analytics_file:
        analytics_json = json.load(analytics_file)

    for bank_account in analytics_json.get('bank_accounts'):
        for period in bank_account.get('periods'):
            uploaded_doc_pk = period.get('uploaded_doc_pk')

            ### GET KEYS RELATED TO ACCOUNT
            for index, keyrow in capt_map.iterrows():
                if keyrow.ocrolus_form != 'BANK_ACCOUNT':
                    continue
                if keyrow.ocrolus_key in bank_account:
                    form_dict = {}
                    form_dict['Vendor_JSON_field_name'] = keyrow.ocrolus_key
                    form_dict['file_name'] = row.file
                    form_dict['ocrolus_doc_type'] = 'BANK_ACCOUNT'
                    form_dict['doc_type'] = keyrow.doc_type
                    form_dict['sub_type'] = keyrow.sub_type
                    form_dict['section_name'] = keyrow.section_name
                    form_dict['attribute_key'] = keyrow.attribute_key

                    ### OCROLUS VALUES
                    form_dict['attribute_value (raw)'] = bank_account.get(keyrow.ocrolus_key)
                    form_dict['attribute_value (normalized)'] = None
                    form_dict['attribute_value_c_score'] = None
                    form_dict['attribute_value_precision_score (optional)'] = None

                    ## LAST 3 COLUMNS. VENDOR INFORMATION
                    form_dict['vendor_product_id'] = 'INSTANT'
                    form_dict['vendor_product_version'] = '1.0'
                    form_dict['vendor_id'] = 'OCROLUS'
                    form_dict['uploaded_doc_pk'] = uploaded_doc_pk
                    capt_list.append(form_dict)
                    capt_list_full.append(form_dict)
            ## GET KEYS RELATED TO PERIOD
            for index, keyrow in capt_map.iterrows():
                if keyrow.ocrolus_form != 'BANK_ACCOUNT':
                    continue
                if keyrow.ocrolus_key in period:
                    form_dict = {}
                    form_dict['Vendor_JSON_field_name'] = keyrow.ocrolus_key
                    form_dict['file_name'] = row.file
                    form_dict['ocrolus_doc_type'] = 'BANK_ACCOUNT'
                    form_dict['doc_type'] = keyrow.doc_type
                    form_dict['sub_type'] = keyrow.sub_type
                    form_dict['section_name'] = keyrow.section_name
                    form_dict['attribute_key'] = keyrow.attribute_key

                    ### OCROLUS VALUES
                    form_dict['attribute_value (raw)'] = period.get(keyrow.ocrolus_key)
                    form_dict['attribute_value (normalized)'] = None
                    form_dict['attribute_value_c_score'] = None
                    form_dict['attribute_value_precision_score (optional)'] = None

                    ## LAST 3 COLUMNS. VENDOR INFORMATION
                    form_dict['vendor_product_id'] = 'INSTANT'
                    form_dict['vendor_product_version'] = '1.0'
                    form_dict['vendor_id'] = 'OCROLUS'
                    form_dict['uploaded_doc_pk'] = uploaded_doc_pk
                    capt_list.append(form_dict)
                    capt_list_full.append(form_dict)
    pass




####
####   instantCaptureFlattenLCMapping
####
def instantCaptureFlattenLCMapping(prj_dir):
    inbound_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    outbound_dir = f'{prj_dir}/outbound/formData'

    ### NEED NEW MAPPING FILE FOR INSTANT (NOT OPTIMA)
    capt_map = pd.read_csv(f'{outbound_dir}/capture_field_mapping.csv')

    df = getFileList(inbound_dir)

    capt_list = []
    capt_list_full = []

    for index, row in df.iterrows():
        capt_json_file = f"{row.file.split('.')[0]}.json"

        with open(f'{outbound_dir}/{capt_json_file}', 'r') as capt_file:
            capt_json = json.load(capt_file)

        # LOOP THROUGH FORMS IN JSON
        for form in capt_json.get('response').get('forms'):
            if form.get('form_type') in ('BANK_ACCOUNT'):
                continue

            if form.get('form_type') == 'W2':
                pass
            form_type = form.get('form_type')

            ### FUZZY MATCHING TO GET FIELDS ACCROSS TAX YEARS (ugh, don't start)
            #can_continue = False
            #for ff in set(capt_map.ocrolus_form.str.lower()):
            #    if ff in form.get('form_type').lower():
            #        can_continue=True
            #if not can_continue:
            #    continue

            for field in form.get('raw_fields'):
                map_res = capt_map[capt_map.apply(lambda x: (x.ocrolus_form.lower() in field.lower() or x.ocrolus_form.lower() == form_type.lower()) and (x.ocrolus_key.lower() in field.lower()),axis=1 )]
                #map_res = capt_map[(capt_map.ocrolus_form.str.lower() in form.get('form_type'))]

                #                                   & (capt_map.ocrolus_key.str.lower().str.contains(field.lower()))]
                if len(map_res) ==0:
                    map_row = None
                elif len(map_res)>1:
                    logging.error(f'mapping issue')
                    map_row = None
                else:
                    map_row = map_res.iloc[0]

                form_dict={}
                form_dict['Vendor_JSON_field_name'] = field
                form_dict['file_name'] = row.file
                form_dict['ocrolus_doc_type'] = form.get('form_type')
                form_dict['doc_type'] = map_row.doc_type if map_row is not None else None
                form_dict['sub_type'] = map_row.sub_type if map_row is not None else None
                form_dict['section_name'] = map_row.section_name if map_row is not None else None
                form_dict['attribute_key'] = map_row.attribute_key if map_row is not None else None

                ### OCROLUS VALUES
                form_dict['attribute_value (raw)'] = form.get('raw_fields').get(field).get('value')
                form_dict['attribute is_empty'] = form.get('raw_fields').get(field).get('is_empty')
                form_dict['attribute_value (normalized)'] = None
                form_dict['attribute_value_c_score'] = None
                form_dict['attribute_value_precision_score (optional)'] = None

                ## LAST 3 COLUMNS. VENDOR INFORMATION
                form_dict['vendor_product_id'] = 'INSTANT'
                form_dict['vendor_product_version'] = '1.0'
                form_dict['vendor_id'] = 'OCROLUS'
                form_dict['passes_validation'] = form.get('passes_validation')
                form_dict['form_uuid'] = form.get('uuid')

                capt_list_full.append(form_dict)  ## ALWAYS ADD TO FULL LIST
                if map_row is not None:
                    capt_list.append(form_dict)   ## ONLY ADD IF THERE'S MAPPING

        appendBSData(prj_dir,row,capt_list,capt_list_full,capt_map)
        appendPSData(prj_dir,row,capt_list,capt_list_full, capt_map)

    ## GET PAGE_INDEXES
    pageIndexDF = pd.read_csv(f'{prj_dir}/outbound/classification/Ocrolus_Instant_Doc_Level.csv')[['form_uuid','page_indexes']]
    pageIndexDF = pageIndexDF[pageIndexDF.form_uuid.notnull()]
    uploadDF = pd.read_csv(f'{prj_dir}/outbound/status/uploadDocs.csv')
    uploadDF = uploadDF[['doc_pk','doc_name']].copy()
    uploadDF['page_indexes'] = '['+uploadDF.doc_name.str.split('(').str[-1].str.split(')').str[0]+']'

    captDF = pd.DataFrame.from_records(capt_list)
    captDF = captDF.merge(pageIndexDF, how='left', on='form_uuid')
    column_to_move = captDF.pop("page_indexes")
    captDF.insert(2, "page_indexes", column_to_move)
    captDF = captDF.merge(uploadDF, how='left', left_on='uploaded_doc_pk', right_on='doc_pk')
    captDF.loc[captDF.page_indexes_x.isnull(), "page_indexes_x"] = captDF.loc[
        captDF.page_indexes_x.isnull(), "page_indexes_y"]
    #captDF.drop(columns=['form_uuid', 'uploaded_doc_pk',
    #   'doc_pk', 'doc_name', 'page_indexes_y'],inplace=True)
    captDF.drop(columns=['uploaded_doc_pk',
       'doc_pk', 'doc_name', 'page_indexes_y'],inplace=True)
    captDF.rename(columns={'page_indexes_x':'page_indexes'},inplace=True)

    captFullDF = pd.DataFrame.from_records(capt_list_full)
    captFullDF = captFullDF.merge(pageIndexDF, how='left', on='form_uuid')
    column_to_move = captFullDF.pop("page_indexes")
    captFullDF.insert(2, "page_indexes", column_to_move)
    captFullDF = captFullDF.merge(uploadDF, how='left', left_on='uploaded_doc_pk', right_on='doc_pk')
    captFullDF.loc[captFullDF.page_indexes_x.isnull(), "page_indexes_x"] = captFullDF.loc[
        captFullDF.page_indexes_x.isnull(), "page_indexes_y"]
    captFullDF.drop(columns=['form_uuid', 'uploaded_doc_pk',
                         'doc_pk', 'doc_name', 'page_indexes_y'], inplace=True)
    captFullDF.rename(columns={'page_indexes_x': 'page_indexes'}, inplace=True)


    ## WRITE TO CSV
    captDF.to_csv(f'{outbound_dir}/Ocrolus_Instant_Field_Level_Mapped_Fields.csv',index=False)
    captFullDF.to_csv(f'{outbound_dir}/Ocrolus_Instant_Field_Level_Mapped_Fields_Full.csv',index=False)


def instantCaptureFlattenNoMapping(prj_dir):
    inbound_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    outbound_dir = f'{prj_dir}/outbound/formData'

    ### NEED NEW MAPPING FILE FOR INSTANT (NOT OPTIMA)
    capt_map = pd.read_csv(f'{outbound_dir}/capture_field_mapping.csv')

    df = getFileList(inbound_dir)

    capt_list = []

    for index, row in df.iterrows():
        capt_json_file = f"{row.file.split('.')[0]}.json"

        with open(f'{outbound_dir}/{capt_json_file}', 'r') as capt_file:
            capt_json = json.load(capt_file)

        # LOOP THROUGH FORMS IN JSON
        for form in capt_json.get('response').get('forms'):
            ### NEED TO ADD FUZZY MATCHING TO GET FIELDS ACCROSS TAX YEARS (ugh, don't start)
            can_continue = False
            for ff in set(capt_map.ocrolus_form.str.lower()):
                if ff in form.get('form_type').lower():
                    can_continue=True
            if not can_continue:
                continue


            for field in form.get('raw_fields'):
                map_res = capt_map[capt_map.apply(lambda x: (x.ocrolus_form.lower() in field.lower()) and (x.ocrolus_key.lower() in field.lower()),axis=1 )]

                if len(map_res) > 0:
                    map_row = map_res.iloc[0]
                else:
                    map_row = None

                form_dict={}
                form_dict['Vendor_JSON_field_name'] = field
                form_dict['file_name'] = row.file
                form_dict['page_indexes'] = form.get('page_indexes')
                form_dict['ocrolus_doc_type'] = form.get('form_type')

                form_dict['doc_type'] = map_row.doc_type if map_row is not None else None
                form_dict['sub_type'] = map_row.sub_type if map_row is not None else None
                form_dict['section_name'] = map_row.section_name if map_row is not None else None
                form_dict['attribute_key'] = map_row.attribute_key if map_row is not None else None

                ### OCROLUS VALUES
                form_dict['attribute_value (raw)'] = form.get('raw_fields').get(field).get('value')
                form_dict['attribute is_empty'] = form.get('raw_fields').get(field).get('is_empty')
                form_dict['attribute_value (normalized)'] = None
                form_dict['attribute_value_c_score'] = None
                form_dict['attribute_value_precision_score (optional)'] = None

                ## LAST 3 COLUMNS. VENDOR INFORMATION
                form_dict['vendor_product_id'] = 'INSTANT'
                form_dict['vendor_product_version'] = '1.0'
                form_dict['vendor_id'] = 'OCROLUS'
                capt_list.append(form_dict)
        appendBSData(prj_dir,row,capt_list,capt_map)
    captDF = pd.DataFrame.from_records(capt_list)
    captDF.to_csv(f'{outbound_dir}/Ocrolus_Instant_Field_Level_Mapped_All_Fields.csv',index=False)


def noMappingExample(prj_dir):
    inbound_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    outbound_dir = f'{prj_dir}/optima_outbound/'

    capt_map = pd.read_csv(f'{outbound_dir}/capture_field_mapping.csv')

    df = getFileList(inbound_dir)
    capt_list = []

    for index, row in df.iterrows():
        opt_json_file = f"{row.file.split('.')[0]}.json"

        with open(f'{outbound_dir}/{opt_json_file}', 'r') as opt_file:
            opt_json = json.load(opt_file)
        if type(opt_json) != list:
            continue

        # LOOP THROUGH FORMS IN JSON
        for form in opt_json:

            for field in form.get('fields'):
                map_res = capt_map[
                    (capt_map.ocrolus_form == form.get('form_type').get('name')) & (capt_map.ocrolus_key == field)]

                if len(map_res) > 0:
                    map_row = map_res.iloc[0]
                else:
                    map_row = None


                form_dict = {}
                form_dict['Vendor_JSON_field_name'] = field
                form_dict['file_name'] = row.file
                form_dict['page_indexes'] = form.get('page_indexes')
                form_dict['ocrolus_doc_type'] = form.get('form_type').get('name')

                form_dict['doc_type'] = map_row.doc_type if map_row is not None else None
                form_dict['sub_type'] = map_row.sub_type if map_row is not None else None
                form_dict['section_name'] = map_row.section_name if map_row is not None else None
                form_dict['attribute_key'] = map_row.attribute_key if map_row is not None else None

                ### OCROLUS VALUES
                form_dict['attribute_value (raw)'] = form.get('fields').get(field)[0].get('value')
                form_dict['attribute_value (normalized)'] = None
                form_dict['attribute_value_c_score'] = form.get('fields').get(field)[0].get('confidence')
                form_dict['attribute_value_precision_score (optional)'] = form.get('fields').get(field)[0].get(
                    'precision')

                ## LAST 3 COLUMNS. VENDOR INFORMATION
                form_dict['vendor_product_id'] = 'OPTIMA'
                form_dict['vendor_product_version'] = '1.0'
                form_dict['vendor_id'] = 'OCROLUS'
                capt_list.append(form_dict)
    captDF = pd.DataFrame.from_records(capt_list)
    captDF.to_csv(f'{outbound_dir}/Ocrolus_Optima_Field_Level_All_Fields.csv', index=False)