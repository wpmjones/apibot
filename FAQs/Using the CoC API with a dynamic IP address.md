# Using the CoC API with a dynamic IP address

## General <a name="1"></a>
Each API Tokens for the Clash of Clans API is restricted to specific IP addresses (IPv4).  This can cause issues when attempting to access it from a connection with a dynamic IP address.

There are a couple of workarounds:

## Use a library with dynamic IP address support <a name="2.1"></a>

A number of the community created API libraries have the ability to create and use a new API token each time your IP address changes.  This happens seamlessly with each request, so enable you to make API requests without needing to manually create a new API Token each time your IP changes.

## Use an API proxy <a name="2.2"></a>

Making your API requests via a proxy will mean that the API will "see" the requests as coming from the IP address of the proxy service.  If you create your token using the IP address of the proxy service and then make your API calls via that service, you will be able to make API requests from any IP address.

One such service is the Royale API proxy.  More details can be found within their documentation:

https://docs.royaleapi.com/#/proxy 
