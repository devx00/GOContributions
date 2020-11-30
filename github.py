"""This module handles requests to the Github API"""
from datetime import datetime
from math import ceil
from threading import RLock
from requests import Session
from json import dumps
from humanize import precisedelta

class GithubAPIException(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__()

    def __str__(self):
        return dumps(self.__dict__)

    def response(self):
        data = dict(self.__dict__)
        del data['status_code']
        return data

class GithubRateLimitExceeded(GithubAPIException):
    def __init__(self, reset):
        timetilactive = reset - datetime.now()
        super().__init__(403, f"Rate Limit Reached. Please try again in {ceil(timetilactive.total_seconds())} seconds")
        self.reset_at = int(reset.timestamp())
        self.reset_utc = reset.isoformat()
        self.reset_nice = f"RateLimit resets in {precisedelta(timetilactive, minimum_unit='seconds')}"


API_LOCK = RLock()
class GithubAPI(Session):
    req_count = 0

    @property
    def req_remaining(self):
        with API_LOCK:
            return self._req_remaining

    @req_remaining.setter
    def req_remaining(self, remaining):
        if type(remaining) is not int:
            try:
                remaining = int(remaining)
            except:
                return
        with API_LOCK:
            self._req_remaining = remaining

    @property
    def req_reset(self):
        with API_LOCK:
            return self._req_reset

    @req_reset.setter
    def req_reset(self, reset):
        if type(reset) is not int:
            try:
                reset = int(reset)
            except:
                return
        with API_LOCK:
            self._req_reset = datetime.fromtimestamp(reset)

    @property
    def counter(self):
        with API_LOCK:
            return GithubAPI.req_count

    @classmethod
    def add_request(cls):
        with API_LOCK:
            cls.req_count += 1
    def __init__(
        self,
        headers={
            'Accept':
            'application/vnd.github.v3+json, application/vnd.github.cloak-preview+json'
        }):
        super().__init__()
        self.req_remaining = 5000
        self.req_reset = datetime.now().timestamp()
        self.headers.update(headers)

    def get(self, *args, **kargs):
        GithubAPI.add_request()
        resp = super().get(*args, **kargs)
        if 'X-RateLimit-Remaining' in resp.headers:
            self.req_remaining = resp.headers['X-RateLimit-Remaining']
            self.req_reset = resp.headers['X-RateLimit-Reset']
        if resp.status_code >= 400:
            self.handle_exception(resp)
        return resp

    def handle_exception(self, resp):
        if resp.status_code == 403 and self.req_remaining == 0:
            raise GithubRateLimitExceeded(self.req_reset)
        else:
            try:
                data = resp.json()
                message = data['message']
            except:
                message = f"An unknown error occurred. API request to {resp.url} returned status {resp.status_code}."
            raise GithubAPIException(resp.status_code, message)

    def set_auth_token(self, token):
        self.headers.update({"Authorization": f"token {token}"})

api = GithubAPI()