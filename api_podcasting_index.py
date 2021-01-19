#! /Library/Frameworks/Python.framework/Versions/3.8/bin/python3.8
# -*- coding: utf-8 -*-

import os
import requests
import time
import hashlib
import config

def search_podcats(name):
    # we'll need the unix time
    epoch_time = int(time.time())
    # our hash here is the api key + secret + time 
    data_to_hash = os.environ['PODCASTING_INDEX_KEY']+ os.environ['PODCASTING_INDEX_SECRET']+ str(epoch_time)
    # which is then sha-1'd
    sha_1 = hashlib.sha1(data_to_hash.encode()).hexdigest()
    headers = {
        'X-Auth-Date': str(epoch_time),
        'X-Auth-Key': os.environ['PODCASTING_INDEX_KEY'],
        'Authorization': sha_1,
        'User-Agent': 'postcasting-index-python-cli'
    }
    url = 'https://api.podcastindex.org/api/1.0/search/byterm?q=' + \
        name+'&type=podcast&only_in=title'
    if config.ACTIVE_LOG:
        print("search_podcats :"+url)    
    response = requests.request('GET', url, headers=headers)
    return response.json()

