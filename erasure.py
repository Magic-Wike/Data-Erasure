"""For UGP Data Erasure Requests...checks Nutshell and Hunter for list of emails. If found, ensure email is opted out or delted"""
import requests
import json
from jsonrpcclient import request, parse, Ok
import config


# step 1: check Nutshell
NUTSHELL_BASE_URL = "http://api.nutshell.com/v1/json"
NUTSHELL_API = config.NUTSHELL_API
USERNAME = 'mwithrow@undergroundshirts.com'
def nutshell_optout(email, opt_out=True, erase_data=False):
    """searches Nutshell for record w/ email address. If found, opt out or delete lead data"""
    api_response = requests.post(NUTSHELL_BASE_URL, json=request("getApiForUsername", params={'username':USERNAME}), timeout=30)
    # print(response.json())
    parsed = parse(api_response.json())
    if isinstance(parsed, Ok):
        login_domain = parsed.result['api']
        endpoint = "https://"+login_domain+"/api/v1/json"
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "searchByEmail",
            "params": {"emailAddressString":email},
            "id": 1,
        }
        json_request = json.dumps(rpc_request)
        print(json_request)
        auth = requests.auth.HTTPBasicAuth(USERNAME,NUTSHELL_API)
        headers = {'Authentication': "true"}
        response = requests.post(endpoint, data=json_request, auth=auth, headers=headers, timeout=30)
        # print(response.json())
        json_response = response.json()
        print(json_response)
        if json_response['result']['contacts']:
            contact_id = json_response['result']['contacts'][0]['id']
            print(contact_id)
        else:
            print('\nEmail not found!')
            return None
        
        def get_contact(contact_id):
            contact_rpc = {
            "jsonrpc": "2.0",
            "method": "getContact",
            "params": {"contactId":contact_id},
            "id": 1,
        }
            try:
                contact_response = requests.post(endpoint, json=contact_rpc, auth=auth, headers=headers, timeout=30)
                # print(contact_response.json())
                contact_json = contact_response.json()
                contact_data = {}
                contact_data['tags'] = contact_json['result']['tags']
                contact_data['contact_rev'] = contact_json['result']['rev']
                associated_leads = contact_json['result']['leads']
                if associated_leads:
                    contact_data['lead_id'] = associated_leads[0]['id']
                    contact_data['lead_rev'] = associated_leads[0]['rev']
                return contact_data

            except Exception as e:
                print(e)
                pass

        # need function to erase data and add opt out tags
        
        contact_data = get_contact(contact_id) #returns Object w/ assoc lead id # + tags if found, returns None if no assoc lead
        if contact_data:
            contact_rev = contact_data['contact_rev']
            tags = contact_data['tags'] # tags are completely replaced if updated. to retain any existing tags, must grab them from get_contact query
            if opt_out:
                tags.append('Email Opt Out')
            try:
                lead_rev = contact_data['lead_rev']
                lead_id = contact_data['lead_id']
            except KeyError:
                lead_id = None
            params = {
                "contactId":contact_id,
                "rev":contact_rev,
                "contact": {"email":None, "tags":tags} # updates email to None (removes) + adds email opt out tag 
            }
            if not erase_data: # if we are not erasing contact, 'update' with existing email (like tags, anything changed will be replaced)
                params["contact"]["email"] = email
            try:
                erase_email_response = requests.post(endpoint, json={"method": "editContact", "params":params}, auth=auth, headers=headers, timeout=30)
                if erase_email_response.status_code in [204, 200, 201]:
                    print('\nEmail and/or tags updated succesfully!')
                else:
                    print(f'\nError! {erase_email_response.status_code}: {erase_email_response.reason}')
            except Exception as e:
                print(e)
                pass
            if lead_id: # if there is a lead associated w/ contact, cancel the lead
                try:
                    delete_lead_response = requests.post(endpoint, json={"method": "deleteLead", "params":{"leadId":lead_id, "rev":lead_rev}}, auth=auth, headers=headers, timeout=30)
                    if delete_lead_response.status_code in [204, 200, 201]:
                        print('\nLead deleted succesfully!')
                    else:
                        print(f'\nError! {delete_lead_response.status_code}: {delete_lead_response.reason}')
                except Exception as e:
                    print(e)
                    pass
            return True
    else:
        pass

def bulk_nutshell_optout(emails, erase_data=False, opt_out=True):
    if type(emails) != list:
        raise TypeError('\nMust pass a list of emails!')
    else:
        success_count, fail_count = 0, 0
        found_emails, not_found_emails = [], []
        for email in emails:
            result = nutshell_optout(email, opt_out=opt_out, erase_data=erase_data)
            if result == True:
                success_count += 1
                found_emails.append(email)
            else:
                fail_count += 1
                not_found_emails.append(email)
    return {'success_count':success_count, 'fail_count':fail_count, 'found_emails':found_emails,'not_found_emails':not_found_emails}
        


# negative result example..
# {'result': {'contacts': [], 'accounts': []}, 'id': '1', 'jsonrpc': '2.0'}
# match found example.. (no assoc lead)
# {'result': {'contacts': [{'stub': True, 'id': 1510627, 'entityType': 'Contacts', 'name': 'Raima Denezez', 'jobTitle': ''}], 'accounts': []}, 'id': '1', 'jsonrpc': '2.0'}
# match found example.. (w/ lead + company)


# step 2: check Hunter