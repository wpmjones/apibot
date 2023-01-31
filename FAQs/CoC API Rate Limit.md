# CoC API Rate Limit

## General information <a name="1"></a>

Each API Token for the Clash of Clans API is to rate limitations.  There isn't an official rate limit figure provided, however we have tested 30-40 requests per second without issues.

If you exceed the rate limit, the API will respond with a `429` error and you will be temporarily unable to make API 
requests with that token (it can last 1 hour).

A number of the community created CoC API libraries have considerations for rate limits included to help avoid exceeding them. 