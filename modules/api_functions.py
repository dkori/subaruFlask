import pandas as pd
import requests

# define a function that returns a dataframe of dealerships within the max distance of the user's zipcode
def get_dealerships(zip_code, max_distance):
    # create the api call url for the given zipcode
    retail_api = 'https://www.subaru.com/services/dealers/distances/by/zipcode?zipcode={zipcode}&count=750&type=Active'.format(
        zipcode=zip_code)
    # call the api and parse json results
    dealer_response = requests.get(retail_api)
    if dealer_response.status_code==200:
        dealer_json = dealer_response.json()
    else:
        return pd.DataFrame({'error': ['Failed to retrieve dealership distances. Please try again later']})
    # create a recursive function that flattens out each item in the dealer_json
    def flatten_recurs(obj):
        flat_dict = {}
        # what to do if obj is a dictionary
        if type(obj) == dict:
            for key in obj.keys():
                if type(obj[key]) not in (list, dict):
                    flat_dict[key] = obj[key]
                else:
                    flat_dict.update(flatten_recurs(obj[key]))
        # what to do if the object is a list
        elif type(obj) == list:
            for subobj in obj:
                flat_dict.update(flatten_recurs(subobj))
        # what to do if the object is a string
        elif type(obj) == str:
            flat_dict[obj] = True
        return flat_dict
    # create a dataframe of all dealerships
    dealer_frame = pd.DataFrame([flatten_recurs(x) for x in dealer_json])
    # return dealer_frame rows where distance is less than the max_distance
    return dealer_frame[dealer_frame['distance'] <= float(max_distance)]


# write a function that takes dealer_frame, max_distance as arguments, and returns a dictionary of inventory
def get_all_inventory(dealer_frame, filter_dict={}):
    # check if the dealer frame api call worked
    if 'error' in dealer_frame.columns:
        return dealer_frame
    # need a function that returns a dictionary parsing out the relevant info for each inventory object,
    # which should correspond to a given car on that dealership
    def parse_inventory_model(obj, dealer_url):
        inventory_dict = {'make and year': obj['title'][0],
                          'model': obj['model'],
                          # 'model_type':obj['title'][1],
                          'condition': obj['condition'],
                          'link': dealer_url + obj['link'],
                          'pricing': obj['pricing']['retailPrice'],
                          'offsite': obj['offSite']}
        if 'fuelType' in obj.keys():
            inventory_dict['fuelType'] = obj['fuelType']
        if len(obj['title']) > 1:
            inventory_dict['edition'] = obj['title'][1]
        # if the condition is pre-owned, check if certified
        if inventory_dict['condition'] == 'Pre-Owned':
            inventory_dict['certified'] = obj['certified']
        # parse out attribute info, which may not be in a straightforward order
        for attr in obj['attributes']:
            inventory_dict[attr['name']] = attr['value']
        return inventory_dict
    # list to store inventory parsed output
    all_inventory_list = list()
    # list to store status codes for error handling
    status_codes = list()
    # iterate through rows of within distance
    for i in range(dealer_frame.shape[0]):
        # limit to row for given dealer
        dealer_row = dealer_frame.iloc[i]
        # extract dealer url
        dealer_url = dealer_row['siteUrl']
        # set dealer_url as referrer in api request header
        headers = {'referrer': dealer_url}
        # make inventory api call url for given dealership
        inventory_url = '{dealer_url}/apis/widget/INVENTORY_LISTING_DEFAULT_AUTO_ALL:inventory-data-bus1/getInventory'.format(dealer_url=dealer_url)
        # apply the model filter, I don't know endpoints for other filters so filter those downstream
        if filter_dict['model'] != '':
            inventory_url += '?model=' + filter_dict['model']
        # call api for inventory_url to get inventory
        inventory_response = requests.get(inventory_url, headers=headers)
        # append status_code to status_codes
        status_codes.append(inventory_response.status_code)
        if inventory_response.status_code==200:
            try:
                inventory = inventory_response.json()['inventory']
            except:
                print('inventory api call did not return valid json')
                print(inventory_response.status_code)
                print(inventory_response.url)
                inventory = None
            try:
                if inventory is not None:
                    # create dataFrame of parsed inventory info
                    dealer_inventory = pd.DataFrame([parse_inventory_model(x, dealer_url) for x in inventory])
                    # add dealer_id to dealer_inventory
                    dealer_inventory['id'] = dealer_row['id']
                    all_inventory_list.append(dealer_inventory)
            except:
                print("inventory api returned valid json, but parse_inventory_model function failed")
                #print(inventory_response.text)
    # return error data frame if all inventory status codes failed
    if not any([x==200] for x in status_codes):
        return pd.DataFrame({'error':['Succeeded in retrieving dealer list, but all API calls for inventory failed. Please try again later']})
    else:
        print("{} dealerships called with API".format(
            str(len([x for x in status_codes if x == 200]))))
    if len(all_inventory_list)>=1:
        all_inventory = pd.concat(all_inventory_list)
        # limit to only new or used based on the user's choice
        print(filter_dict['condition'])
        if filter_dict['condition'] != 'Both':
            print("condition filter triggered")
            all_inventory = all_inventory[all_inventory['condition'].str.contains(filter_dict['condition'])]
        # loop through remaining filters in filter_frame
        for key in filter_dict.keys():
            if key not in ['model', 'zip_code', 'max_distance', 'condition'] and filter_dict[key] != '':
                all_inventory = all_inventory[all_inventory[key].str.contains(filter_dict[key], na=False)]
        return all_inventory.merge(dealer_frame, on='id')
    else:
        return pd.DataFrame({'error': [
            'No dealerships nearby have inventory that match your search']})
