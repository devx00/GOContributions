Setup
====
Prerequisites
- python3.7+
- pip
- pipenv # Not strictly necessary but highly recommended.
- A github personal access token for API access.

Starting the server locally:
```bash
git clone https://github.com/zachhanson94/GOContributions.git
cd GOContributions
pipenv install
echo "GITHUB_TOKEN=${GITHUB_TOKEN}" > .env
pipenv run ./app.py
```

Endpoints
====
# GET /<Organization Name\>

## Query Params:
**per_page**: Number of contributors per page. Default: 20, max: 100
**page**: The page of data to return. Default: 1
**cache**: Whether to use a cached value if available. revalidate will bypass any cached responses but it won't flush the entire cache. Repositories will be refreshed individually. Options: true,false,revalidate Default: true

## Request Headers:
**If-Modified-Since**: A UTC time string used to conditionally request data only if its newer than the sent time. See the Last-Modified response header for possible values.
**Cache-Control**: Cache control instructions. Implemented values: No-Cache, Must-Revalidate. Default: None

## Response Headers:
**Last-Modified**: This is the last time that any of the orgs repositories were pushed to. Can be used for checking if cached values are still relevant.

## Response Codes:
**200**: Ok. Request completed successfully and data should be returned in the body.
**304**: Not Modified. Sent if request specified a If-Modified-Since header and the data has not been modified since.
**403**: Forbidden. Happens if the Github API returns a 403. Typically is caused by a Rate Limit issue. If rate limit information is available it is returned in the response.
**500**: Unknown. An unexpected error occurred. May or may not contain contextual data in the body.



## Standard Cache Policy:
Responses are cached for 1 hour unless otherwise specified.
Repository information is cached indefinitely but is validated by checking the pushed_at value. Repositories can be refreshed independently of one another so an update to 1 repo does not require the entire org cache to be destroyed. This is very useful because loading contributors for **ALL** repositories of an org can be very time and API Rate Limit consuming.

