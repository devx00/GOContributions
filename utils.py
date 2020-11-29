"""Some Utility Functions"""
from json.decoder import JSONDecodeError
from threading import Thread
from queue import Empty, Queue
from typing import Any, Callable, Iterable, List
from github import api

def format_top_contributer(contrib):
    """Takes the temp form of contributor and returns the data rep for response"""
    data = dict(contrib)
    cmessage = data['last_commit']['message']
    del data['last_commit']
    data['commit'] = cmessage
    return data

def parse_next_page(resp):
    if "Link" in resp.headers:
        for link in resp.headers['Link'].split(","):
            link_url, link_rel = link.strip().split("; ")
            if "next" in link_rel:
                return link_url.strip("<").strip(">")

def fetch_page(url, page=1, per_page=100, params={}):
    params.update({'per_page': per_page, 'page': page})
    resp = api.get(url, params=params)
    return resp

def fetch(url, per_page, params={}):
    params.update({'per_page': per_page})
    resp = api.get(url, params=params)
    try:
        data = resp.json()
    except JSONDecodeError:
        data = []
    return data, parse_next_page(resp)

def fetch_all(url, per_page=100, params={}):
    next_page = url
    while next_page is not None:
        page_data, next_page = fetch(next_page, per_page, params=params)
        for obj in page_data:
            yield obj

def fetch_all_async(url, q, per_page=100, params={}):
    next_page = url
    while next_page is not None:
        page_data, next_page = fetch(next_page, per_page, params=params)
        for obj in page_data:
            q.put(obj)

def fetch_async(url, per_page=100, params={}, maxsize=200):
    q = Queue(maxsize=maxsize)
    t = Thread(target=fetch_all_async, args=(url, q, per_page, params))
    t.start()
    while nextval := q.get():
        if nextval is None:
            break
        yield nextval
        q.task_done()
        print(q.qsize())


