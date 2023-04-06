# CoC API Response Caching

## General <a name="1"></a>

Each API response from the Clash of Clans API is cached for a certain amount of time.  This means that the response will not change until the cache timer has expired, therefore there isn't any benefit from repeating the request again until this time.  The cache timer varies by API endpoint:

**Clan** - 120 seconds (2 minutes)
**War** - 600 seconds (10 minutes)
**Player** - 60 seconds (1 minute)

When making an API request, you can check the response headers for a `cache-control` header and the value of this is the number of seconds until the cache expires.