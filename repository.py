"""
This module handles all actions pertaining to Github Repositories.
"""

from cache import StoredLRUCache
from datetime import datetime, timezone
from math import ceil
from typing import Optional
from utils import fetch_all, fetch_async
from cachetools import LRUCache
from collections import OrderedDict
from threading import RLock, Thread
from github import api

class RepositoryException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

def contributor_count(contrib):
    """Cache helper method to determine size of contributors cache"""
    return len(contrib[1])

def load_last_commit(repo, contributor):
    url = f"{repo.url}/commits"
    cmauthor = "author"
    def get_commit():
        resp = api.get(url,
                    params={cmauthor:contributor['username'], 'per_page': 1})
        return resp.json()
    commits = get_commit()
    if len(commits) < 1:
        cmauthor = "committer"
        commits = get_commit()

    commit = commits[0]
    commitdate = commit['commit'][cmauthor]['date']
    commitdate = datetime.strptime(commitdate,"%Y-%m-%dT%H:%M:%S%z")
    commitmessage = commit['commit']['message']
    email = commit['commit'][cmauthor]['email']

    contributor['email'] = email
    contributor['last_commit'] = {
        "message": commitmessage,
        "date": commitdate
    }


class Repository:
    cache = StoredLRUCache(maxsize=10000, getsizeof=contributor_count, path="data/repository.cache")
    cachelock = RLock()
    @property
    def fully_loaded(self):
        return (not self.needs_load and 
                len(self.contrib_need_update) == 0)

    @property
    def cachesize(cls):
        return cls.cache.maxsize

    @cachesize.setter
    def set_cachesize(cls, newsize):
        cls.cache = StoredLRUCache(maxsize=newsize, getsizeof=contributor_count, path=Repository.cache.savepath)

    @property
    def commit_iter(self):
        if "_commit_iter" not in self.__dict__:
            self._commit_iter = iter(fetch_all(f"{self.url}/commits"))
            # self._commit_iter = iter(fetch_async(f"{self.url}/commits"))
        return self._commit_iter

    def __init__(self,
                name: str,
                url: str,
                last_push: datetime,
                force_refresh=False):
        """Init the repository identified by {url}.

        Initialized the repository then attempts to load 
        the repository's contributors from the cache.

        Args:
            self: self
            url: The repository's url.
            last_push: When the last push to the repository was.
            force_refresh: If true, ignores cached data and loads entirely fresh.
        """

        c_last_push = None
        contributors = OrderedDict()
        try:
            with Repository.cachelock:
                if force_refresh:
                    del Repository.cache[url]
                else:
                    c_last_push, contributors = Repository.cache[url]
        except KeyError:
            pass

        self.name = name
        self.url = url
        self.last_push = last_push
        self.needs_load = c_last_push != last_push
        self.contributors = contributors
        self.contrib_need_update = set()

    def store(self):
        with Repository.cachelock:
            Repository.cache[self.url] = (self.last_push, self.contributors)
            Repository.cache.save()


    def load_contributors(self):
        """Loads the contributors for this repository.

        If `needs_load` is True then it fetches all the
        contributors from the server, and then proceeds to
        load the last_commit for any contributor whose contributions
        count does not match the cached one.

        Raises:
            RepositoryException:
                Something went wrong loading the repository.
        """

        if not self.needs_load:
            for contrib in self.contributors.values():
                if contrib['last_commit'] is None:
                    self.contrib_need_update.add(contrib['username'])
            return
        try:
            newcontrib = OrderedDict()
            for contrib in fetch_all(f"{self.url}/contributors"):
                id = contrib['login']
                last_commit = None
                email = None
                if (id in self.contributors and
                    self.contributors[id]['contributions'] == contrib['contributions']):
                    last_commit = self.contributors[id]['last_commit']
                    email = self.contributors[id]['email']

                if last_commit is None:
                    self.contrib_need_update.add(id)

                newcontrib[id] = {
                    "username": contrib['login'],
                    "email": email,
                    "image": contrib['avatar_url'],
                    "contributions": contrib['contributions'],
                    "last_commit": last_commit
                }

            self.contributors = newcontrib
            self.needs_load = False
            self.store()

        except Exception as e:
            raise RepositoryException((f"Failed to load contributors"
                                       f" for repository: {self.name}"))


    def load_last_commits(self, only:Optional[set]=None):
        """Load the last commit for each contributor
        
        Start iterating over each commit adding last_commits to contributors
        as they come up. If `only` set is passed then break once all contributors
        in only have their last_commits assigned.

        Args:
            only: Optional; 
                A set of usernames/logins that we need last_commits for now. If
                specified this function will break once all are accounted for and
                any subsequent calls to load_last_commits will continue where the 
                commit_iter left off.
        """
        if ((only and
            len(self.contrib_need_update.intersection(only)) == 0) or
            len(self.contrib_need_update) == 0):
            return
        count = 0
        found = 1
        for commit in self.commit_iter:
            count += 1
            needed = self.contrib_need_update.intersection(only) if only else self.contrib_need_update
            try:
                if ((commit['author'] and
                    commit['author']['login'] in self.contrib_need_update) or (
                        commit['committer'] and
                        commit['committer']['login'] in self.contrib_need_update
                    )):

                    cmauthor = "author" if (commit['author'] and
                    commit['author']['login'] in self.contrib_need_update) else "committer"

                    author = commit[cmauthor]['login']
                    commitdate = commit['commit'][cmauthor]['date']
                    commitdate = datetime.strptime(commitdate,"%Y-%m-%dT%H:%M:%S%z")
                    commitmessage = commit['commit']['message']
                    email = commit['commit'][cmauthor]['email']

                    self.contributors[author]['email'] = email
                    self.contributors[author]['last_commit'] = {
                        "message": commitmessage,
                        "date": commitdate
                    }
                    self.contrib_need_update.remove(author)
                    if author in needed:
                        found += 1

                    if (len(needed) == 0):
                        break
                if found / ceil(count / 100) < 0.25 and len(needed) <= 10:
                    threads = []
                    for username in needed:
                        t = Thread(target=load_last_commit, args=(self, self.contributors[username]))
                        threads.append(t)
                        t.start()
                        self.contrib_need_update.remove(username)
                    for t in threads:
                        t.join()
                    break

            except Exception as e:
                print(f"Loading commits failed on commit: {commit}")
                raise e
        self.store()
