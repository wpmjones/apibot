# Using the CoC API with BDFD

## Introduction <a name="1"></a>

Bot Designer For Discord (BDFD) is a free to use Discord bot maker.  In order to use the Clash of Clans API with BDFD, you will need to make provisions for using the Clash of Clans API with a dynamic IP address.

This guide is provided "as is", the majority of bot developers in this community use mainstream development languages.

Follow the instructions for using the Royale API Proxy service for the Clash of Clans API:

https://docs.royaleapi.com/#/proxy

- Create a BDFD variable named coc_token with your API Token

- Include in your command for any api calls the following code snippet:
    ```
    $httpAddHeader[Authorization;Bearer $getVar[coc_token]]
    $httpAddHeader[Accept;application/json]
    $httpGet[https://cocproxy.royaleapi.dev/v1/endpoint_details]
    ```

where you can replace endpoint_details with the URL details of the endpoint you want to use. Make sure to replace the # of every tag with `%23` in the request URL

❗ If you don't get any message when you execute your command, it could be that the text you are trying to send exceeds the character limit of Discord messages/embeds.

## Example <a name="2"></a>

```
$try
$nomention
$reply
$httpAddHeader[Authorization; Bearer $getVar[coc_token]]
$httpAddHeader[Accept;application/json]
$httpGet[https://cocproxy.royaleapi.dev/v1/players/%232PP]
$title[Player information - $httpResult[name]]
$addField[Tag; $httpResult[tag]]
$addField[Townhall level; $calculate[$httpResult[townHallLevel]]]
$addField[Expirience Level; $calculate[$httpResult[expLevel]]] 

$catch
  $color[E74C3C]
  $title[Error Handling]
  $addField[Function:;$error[command]]
  $addField[Error:;$error[message]]
$endtry
```