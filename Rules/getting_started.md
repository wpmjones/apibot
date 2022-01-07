# Clash API Developers - Getting Started
## Table of Content
1. [Clash of Clans API](#1)

## Clash of Clans API <a name="1"></a>
Clash of Clans has an official [API](https://developer.clashofclans.com/#/) with a developer console that you will 
have to register with. You can find their documentation [here](https://developer.clashofclans.com/#/documentation). 
The purpose of creating an account is to create a [JSON Web Token](https://jwt.io/introduction). 
These tokens are proof that you are authorized to request data from the CoC API endpoint. 
Therefore, every request you make to the API MUST have the token you created. 
This token is, however, tied to your public IP. If you created a token for your development workstation with IP A 
and then deploy your application to a server that has an IP of B. Then your request will be denied. 
You will need to create a token for each public IP you are interacting with the API. 

### Querying without a JWT token
![With not JWT](images/img_getting_started/01_curl_no_jwt.png)
### Querying with a JWT token
![With JWT](images/img_getting_started/02_curl_with_jwt.png)
