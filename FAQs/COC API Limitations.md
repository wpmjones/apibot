# COC API Limitations

## Things you can't do/not given in the API <a name="1"></a>

- get building levels
- get/send clan chat or clan mails
- get the details of a regular war or warlog if it is set to private
- change anything in game for a clan or player, i.e war preference or clan description
- images/assets are not given, except for league badges & clan badges (there are other places to get assets however)
- cannot build bases, there is no way to generate a base link
- no historical stats (except legend league standings), like previous clan history or names of a player
- no access to a player's upgrade timers, whether it's builder or labs
- get pending donation requests
- purchase history, which is for the better, but you can’t get info on their skins, sceneries, or gold pass status
- a player’s location (unless they hit top 200 in a local legend leaderboard)
- cannot get info on where capital gold was donated
- no Events (some wrapper have events by caching and comparing)

## Known Limitations <a name="2"></a>

- previous war data is not fleshed out in the war log endpoint (in contrary to the documentation)
- clan capital contributions/clan game contributions have no endpoint, can only be found by polling the player's achievements
- members in the clan endpoint do not give player town hall level
- the api uses a cache & is not real time -> times are 1/2/10 minutes for the player/clan/war endpoints respectively
- api tokens are tied to ip (can get around this by using a library that handles ur token generation for u or proxy api)
- minor, but newly created accounts may not show up in the player endpoint
- minor, but banned players may show up in the clan member list for some time
- minor, but builder base prestige isn't accessible