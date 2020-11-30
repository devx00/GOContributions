"""
This module handles all actions pertaining to Github Organizations.
"""
import pytz
from cache import StoredLRUCache
from math import ceil
from cachetools import cache

from cachetools.lru import LRUCache
from utils import fetch_all
from repository import Repository
from github import api
from typing import List
from datetime import datetime,timezone
from threading import RLock, Thread
from queue import Queue

commitcache = StoredLRUCache(maxsize=100000, path="data/org.cache")
commitcache_lock = RLock()

def uncache(usernames, org):
    with commitcache_lock:
        for username in usernames:
            key = f"{org.name}/{username}"
            if key in commitcache:
                del commitcache[key]

def load_last_commit(org, contributor):
    """Loads a contributors last commit directly.

    This is much quicker than iterating through the commits.
    The problem is, we only have approximately 30 req per minute on this endpoint so it is hard to determine when we should use it and when not to.
    """ 
    cachekey = f"{org.name}/{contributor['username']}"
    with commitcache_lock:
        if cachekey in commitcache:
            contributor['email'] = commitcache[cachekey]['email']
            contributor['last_commit'] = commitcache[cachekey]['last_commit']
            return
    url = "https://api.github.com/search/commits"
    q = f"author:{contributor['username']} org:{org.name}"
    sort = "author-date"
    order = "desc"
    per_page = 1
    resp = api.get(url, params={'q': q, 'sort':sort, 'order':order, 'per_page': per_page})
    data = resp.json()
    commit = data[0]
    commitdate = commit['commit']['author']['date']
    commitdate = datetime.strptime(commitdate,"%Y-%m-%dT%H:%M:%S%z")
    commitmessage = commit['commit']['message']
    email = commit['commit']['author']['email']

    contributor['email'] = email
    contributor['last_commit'] = {
        "message": commitmessage,
        "date": commitdate
    }
    with commitcache_lock:
        commitcache[cachekey] = {
            'email': contributor['email'],
            'last_commit': contributor['last_commit']
        }
    


class OrganizationException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__()

    def __str__(self):
        return self.message

class OrganizationNotFoundException(OrganizationException):
    """This exception is raised whenever an organization is not found"""
    pass

class RepoContribLoader(Thread):
    @classmethod
    def load(cls, repos, fn=lambda repo: repo.load_contributors()):
        num_threads = len(repos)
        inqueue = Queue()
        outqueue = Queue()
        threads = []
        for repo in repos:
            inqueue.put_nowait(repo)
        for _ in range(num_threads):
            t = RepoContribLoader(inqueue, outqueue, fn=fn)
            threads.append(t)
            t.start()
        count = len(repos)
        while count > 0:
            repo = outqueue.get()
            count -= 1
            yield repo
            outqueue.task_done()

        for t in threads:
            t.join()

    def __init__(self,
                inq,
                outq,
                fn=lambda repo: repo.load_contributors(),
                *args,
                **kargs):

        self.inq = inq
        self.outq = outq
        self.fn = fn
        super().__init__(*args, **kargs)

    def run(self):
        while self.inq.qsize() > 0:
            repo = self.inq.get_nowait()
            self.fn(repo)
            self.outq.put_nowait(repo)
            self.inq.task_done()


class Organization:

    daemon_threads = {}
    @property
    def endpoint(self) -> str:
        return f"https://api.github.com/orgs/{self.name}"

    @property
    def last_changed(self):
        return max(map(lambda r: r.last_push, self.repositories)).astimezone(pytz.timezone("GMT"))

    def __init__(self, name: str, force_refresh=False):
        self.name = name
        self.repositories: List[Repository] = []
        self.contributors: List[dict] = []
        self.force_refresh = force_refresh
        self.contributors_loaded = False
        if force_refresh:
            if self.name in Organization.daemon_threads:
                del Organization.daemon_threads[self.name]
        self.load_repositories()

    def load_repositories(self):
        """Attempt to load the orgs repositories."""

        for repo in fetch_all(f"{self.endpoint}/repos"):
            name = repo['name']
            url = repo['url']
            if repo['pushed_at'] is not None:
                last_push = datetime.strptime(repo['pushed_at'],
                                            "%Y-%m-%dT%H:%M:%S%z")
                self.repositories.append(Repository(name, url, last_push, self.force_refresh))
        for repo in self.repositories:
            if repo.needs_load and len(repo.contributors) > 0:
                uncache(repo.contributors.keys(), self)

    def changed_since(self, dt:datetime):
        """Check if any repositories have been pushed since the specified date `dt`."""

        return self.last_changed > dt

    def load_contributors(self) -> List[dict]:
        """Loads the orgs contributors sorted by number of contributions.

        Loads the contributors from each repository then sorts them by total contributions.
        The `last_commit` for each contributor is not loaded at this point. This is just to determine the order of contributors. The `last_commit` is loaded asynchronously or when that contributor is being included in a page of results. This allows for efficient(ish) paging of results.
        """
        if not self.contributors_loaded:
            contributors = {}
            for repo in iter(RepoContribLoader.load(self.repositories)):
                for n, contributor in repo.contributors.items():
                    if n not in contributors:
                        contributors[n] = dict(contributor)
                        contributors[n]['last_commit'] = None
                    else:
                        contributors[n]["contributions"] += contributor["contributions"]
            self.contributors = sorted(contributors.values(), key=lambda c: c['contributions'], reverse=True)
            self.contributors_loaded = True
        return self.contributors

    def get_top_contributors(self, count=None, page=1):
        """Load the top contributors for the org.

        Get the top `count` contributors, offset by `count * (page - 1)`.
        Load the last commit for each top contributor in each repository, if it exists.
        Find the most recent one among all the repos and include that one in the contributor's object.
        return the contributors.

        Args:
            count: The number of contributors to return.
            page: The page number to return. Uses count to determine offset.
        """

        self.load_contributors()
        count = count or len(self.contributors)
        end = page * count
        start = end - count
        num_pages = ceil(len(self.contributors)/count)
        if page < 1 or page > num_pages:
            return [], num_pages
        top_contributors = self.contributors[start:end]
        have_last = set([contrib['username'] for contrib in top_contributors if contrib['last_commit'] is not None])

        req_logins = set(map(lambda contrib: contrib['username'], top_contributors)).difference(have_last)
        fn = lambda repo: repo.load_last_commits(only=req_logins)
        for repo in RepoContribLoader.load(self.repositories, fn):
            for contrib in top_contributors:
                if contrib['username'] in repo.contributors:
                    repo_contrib = repo.contributors[contrib['username']]
                    try:
                        if (contrib['last_commit'] is None or
                            contrib['last_commit']['date'] < repo_contrib['last_commit']['date']):
                            contrib['last_commit'] = repo_contrib['last_commit']
                            contrib['email'] = repo_contrib['email']
                    except:
                        print(f"Failed: {repo.name}, {contrib['username']}")
                        print(repo_contrib)

        return top_contributors, num_pages

    def daemon_loader(self):
        """Starts a cache pre-loader daemon"""

        if (not all(map(lambda r: r.fully_loaded, self.repositories)) and
            self.name not in Organization.daemon_threads):
            t = Thread(target=self.get_top_contributors, daemon=True)
            t.start()
            Organization.daemon_threads[self.name] = t

