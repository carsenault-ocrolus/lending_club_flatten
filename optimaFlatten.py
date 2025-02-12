from helper_functions import *
from datetime import datetime


def optimaClassificationFlatten(prj_dir):
    inbound_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    outbound_dir = f'{prj_dir}/optima_outbound/'

    df = getFileList(inbound_dir)
    opt_timing_df = pd.read_csv(f'{outbound_dir}/optima_upload_timing.csv')
    class_list = []

    for index, row in df.iterrows():
        opt_json_file = f"{row.file.split('.')[0]}.json"

        with open(f'{outbound_dir}/{opt_json_file}', 'r') as opt_file:
            opt_json = json.load(opt_file)
        if type(opt_json) != list:
            form_dict={}
            form_dict['file_name'] = row.file
            form_dict['doc_status'] = 'ERROR'
            form_dict['doc_status_reason_code'] = opt_json.get('message')
            class_list.append(form_dict)
            continue

        # LOOP THROUGH FORMS IN JSON
        for form in opt_json:
            form_dict={}
            form_dict['file_name'] = row.file
            form_dict['page_indexes'] = form.get('page_indexes')
            form_dict['doc_type'] = None
            form_dict['doc_type_c_score'] = None
            form_dict['sub_type'] = form.get('form_type').get('name')
            form_dict['sub_type_c_score'] = form.get('form_type').get('precision') if form.get('form_type').get('precision') is not None else 0
            for key in ['legible_quality','quality_score','quality_c_score','fraudulent','trust_score','completeness','completeness_score','completeness_c_score',
                        'correctness','correctness_c_score']:
                form_dict[key] = None

            # Parse the string into a datetime object
            upload_row = opt_timing_df[opt_timing_df.file == row.file].iloc[0]
            time_format = '%Y-%m-%d %H:%M:%S.%f'
            start_time = datetime.strptime(upload_row.start_time, time_format)
            end_time = datetime.strptime(upload_row.end_time, time_format)
            diff_time = end_time-start_time
            start_time = start_time.isoformat()
            end_time = end_time.isoformat()
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
            form_dict['doc_page_count'] = len(form.get('page_indexes'))
            form_dict['doc_status'] = 'SUCCESS'
            form_dict['vendor_product_id'] = 'OPTIMA'
            form_dict['vendor_product_version'] = '1.0'
            form_dict['vendor_id'] = 'OCROLUS'
            class_list.append(form_dict)
    classDf = pd.DataFrame.from_records(class_list)
    classDf.to_csv(f'{outbound_dir}/Ocrolus_Optima_Doc_Level.csv',index=False)

def optimaCaptureFlattenLCMapping(prj_dir):
    inbound_dir = f'{prj_dir}/inbound/Ocrolus Confidential and Private Data/'
    outbound_dir = f'{prj_dir}/optima_outbound/'

    capt_map = pd.read_csv(f'{outbound_dir}/capture_field_mapping.csv')

    df = getFileList(inbound_dir)
    opt_timing_df = pd.read_csv(f'{outbound_dir}/optima_upload_timing.csv')
    capt_list = []

    for index, row in df.iterrows():
        opt_json_file = f"{row.file.split('.')[0]}.json"

        with open(f'{outbound_dir}/{opt_json_file}', 'r') as opt_file:
            opt_json = json.load(opt_file)
        if type(opt_json) != list:
            continue

        # LOOP THROUGH FORMS IN JSON
        for form in opt_json:
            if form.get('form_type').get('name') not in set(capt_map.ocrolus_form):
                continue

            for field in form.get('fields'):
                map_res = capt_map[(capt_map.ocrolus_form == form.get('form_type').get('name')) & (capt_map.ocrolus_key==field)]
                if len(map_res) ==0:
                    continue
                elif len(map_res)>1:
                    print('mapping issue')

                map_row = map_res.iloc[0]

                form_dict={}
                form_dict['Vendor_JSON_field_name'] = field
                form_dict['file_name'] = row.file
                form_dict['page_indexes'] = form.get('page_indexes')
                form_dict['ocrolus_doc_type'] = form.get('form_type').get('name')
                form_dict['doc_type'] = map_row.doc_type
                form_dict['sub_type'] = map_row.sub_type
                form_dict['section_name'] = map_row.section_name
                form_dict['attribute_key'] = map_row.attribute_key

                ### OCROLUS VALUES
                form_dict['attribute_value (raw)'] = form.get('fields').get(field)[0].get('value')
                form_dict['attribute_value (normalized)'] = None
                form_dict['attribute_value_c_score'] = form.get('fields').get(field)[0].get('confidence')
                form_dict['attribute_value_precision_score (optional)'] = form.get('fields').get(field)[0].get('precision')

                ## LAST 3 COLUMNS. VENDOR INFORMATION
                form_dict['vendor_product_id'] = 'OPTIMA'
                form_dict['vendor_product_version'] = '1.0'
                form_dict['vendor_id'] = 'OCROLUS'
                capt_list.append(form_dict)
    captDF = pd.DataFrame.from_records(capt_list)
    captDF.to_csv(f'{outbound_dir}/Ocrolus_Optima_Field_Level_Mapped_Fields.csv',index=False)


def optimaCaptureFlattenNoMapping(prj_dir):
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