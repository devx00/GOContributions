#!/usr/bin/env python3
from os import getenv
from dotenv import load_dotenv
from typing import Optional, Tuple, Union
from github import GithubAPIException
from utils import format_top_contributer
from flask import Flask,request, jsonify, render_template
from organization import Organization
from cache import CacheControl, ResponseCache
from github import api
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
DEBUG = False
load_dotenv()
api.set_auth_token(getenv("GITHUB_TOKEN"))
if DEBUG:
    import urllib3
    urllib3.disable_warnings()
    api.proxies = {'https': 'http://localhost:8080', 'http': 'localhost:8080'}
    api.verify = False
maincache = ResponseCache()

@app.route("/", methods=["GET"])
def root():
    return render_template('index.html')

@app.route('/<orgname>') #type: ignore
def organization(orgname: str) -> Union[Optional[str] , Tuple[Optional[str], int]]:
    cachetype = CacheControl.parse_cachecontrol(request)
    force_refresh = cachetype == CacheControl.NoCache
    org = Organization(orgname, force_refresh)

    if cachetype == CacheControl.CacheOK:
        if pair := maincache.get_withargs(orgname, request.args):
            if pair[0] is not None and pair[1] is not None:
                resp = pair[0]
                date_changed = pair[1]
                headers = {'Last-Modified': CacheControl.get_modifiedsince(date_changed)}
                return jsonify(resp), 200, headers #type: ignore
    if cachetype == CacheControl.IfUnchangedSince:
        since = cachetype.parse_modifiedsince(request)
        if since and not org.changed_since(since):
            return ('', 304, {
                'Last-Modified': CacheControl.get_modifiedsince(org.last_changed)
            })  #type: ignore

    per_page = min(int(request.args.get('per_page', '20')), 100)
    page = int(request.args.get('page', '1'))
    top, pages = org.get_top_contributors(per_page, page)
    count_contrib = len(org.contributors)
    org.daemon_loader()
    top_formatted = list(map(format_top_contributer, top))
    data = {
        "navigation": {
            "page": page,
            "per_page": per_page,
            "total_contributors": count_contrib,
            "total_pages": pages
        },
        'data': top_formatted
    }
    maincache.store_withargs((data, org.last_changed), org, request.args)
    return jsonify(data), {
        'Last-Modified': CacheControl.get_modifiedsince(org.last_changed)
    } #type: ignore

@app.errorhandler(GithubAPIException)
def api_error(error):
    return jsonify(error.response()), error.status_code

if __name__ == '__main__':
    app.run()