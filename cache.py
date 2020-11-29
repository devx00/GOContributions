"""This module handles caching."""
import pickle
import pytz
from cachetools.cache import Cache
import flask
from typing import Dict, Optional, Tuple
from cachetools import LRUCache, TTLCache
from datetime import datetime, timezone
from pathlib import Path
from enum import Enum

class CacheControl(Enum):
    NoCache = 1
    Revalidate = 2
    IfUnchangedSince = 3
    CacheOK = 4

    @classmethod
    def parse_cachecontrol(cls, request: flask.Request):
        if 'cache' in request.args:
            cacheval = request.args['cache'].lower()
            if cacheval in ["true", True, "yes", "1"]:
                return CacheControl.CacheOK
            elif cacheval in ["false", False, "no", "0"]:
                return CacheControl.NoCache
            elif cacheval in ['revalidate', 'validate']:
                return CacheControl.Revalidate
        if "Cache-Control" in request.headers:
            cacheval = request.headers['Cache-Control'].lower()
            if cacheval in [
                "no-cache",
                "must-revalidate"
            ]:
                return CacheControl.NoCache if cacheval == "no-cache" else CacheControl.Revalidate
        elif "If-Modified-Since" in request.headers:
            return CacheControl.IfUnchangedSince

        return CacheControl.CacheOK
    
    @classmethod
    def get_modifiedsince(cls, date):
        dateformat = "%a, %d %b %Y %H:%M:%S %Z"
        return date.astimezone(pytz.timezone("GMT")).strftime(dateformat)
    
    def parse_modifiedsince(self, request):
        datestring = request.headers['If-Modified-Since']
        dateformat = "%a, %d %b %Y %H:%M:%S %Z"
        try:
            date = datetime.strptime(datestring, dateformat).replace(tzinfo=pytz.timezone("GMT"))
            return date
        except:
            return None




class StoredLRUCache(LRUCache):

    @property
    def savepath(self) -> Optional[str]:
        return self._path

    @savepath.setter
    def savepath(self, path):
        if path is None:
            return
        self._path = path
        pathl = Path(self._path)
        if pathl.is_file():
            try:
                p = pathl.open('rb')
                self.__dict__ = pickle.load(p)
            except:
                pass

    def __init__(self, path=None, *args, **kargs):
        super().__init__(*args, **kargs)
        self.savepath = path

    def save(self):
        if self.savepath is None:
            return
        try:
            path = Path(self.savepath)
            path.touch()
            p = path.open("wb")
            pickle.dump(self.__dict__, p)
        except Exception as e:
            print(e)


class ResponseCache(TTLCache):

    def __init__(self, maxsize=1000000, ttl=(60*60)):
        super().__init__(maxsize=maxsize, ttl=ttl)

    def key_fromargs(self, org, args):
        try:
            if type(org) is str:
                key = org
            else:
                key = org.name
            per_page = args.get('per_page', '20')
            page = args.get('page', '1')
            key += f"&per_page={per_page}"
            key += f"&page={page}"
            return key
        except:
            return None

    def store_withargs(self, value, org, args):
        key = self.key_fromargs(org, args)
        if key is not None:
            self[key] = value

    def get_withargs(self, org, args) -> Tuple[Optional[dict], Optional[datetime]]:
        key = self.key_fromargs(org, args)
        if key is not None:
            try:
                return self[key]
            except KeyError:
                return (None, None)
        else:
            return (None, None)




