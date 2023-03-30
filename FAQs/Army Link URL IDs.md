# Army Link URL IDs

## General <a name="1"></a>

Army Link URLs enable sharing of army compositions externally from the Clash of Clans game client.  Other players can then use the link to import the army composition to one of their army slots in game.  These URLs can be generated programatically if you know the troop and spell IDs.

Example of a simple army link breakdown:

https://link.clashofclans.com/en?action=CopyArmy&army=u10x0-2x3s1x9-3x2

First are troops, prefixed with the "u" character):
First item is 10 troops with id 0, which are Barbarians.
Next item is 2 troops with id 3, which are Giants.

Then come the spells (starting with the s character):
First is 1 spell with id 9, which is a Poison Spell.
Second is 3 spells with id 2, which is a Rage Spell.

The `army=` querystring value can be parsed with regex into two groups (troops and spells):

`u([\d+x-]+)s([\d+x-]+)`

## (Super-) Troops <a name="2.1"></a>

```
 0 - Barbarian
 1 - Archer
 2 - Goblin
 3 - Giant
 4 - Wall Breaker
 5 - Balloon
 6 - Wizard
 7 - Healer
 8 - Dragon
 9 - P.E.K.K.A
10 - Minion
11 - Hog Rider
12 - Valkyrie
13 - Golem
15 - Witch
17 - Lava Hound
22 - Bowler
23 - Baby Dragon
24 - Miner
26 - Super Barbarian
27 - Super Archer
28 - Super Wall Breaker
29 - Super Giant
53 - Yeti
55 - Sneaky Goblin
56 - Super Miner
57 - Rocket Balloon
58 - Ice Golem
59 - Electro Dragon
63 - Inferno Dragon
64 - Super Valkyrie
65 - Dragon Rider
66 - Super Witch
76 - Ice Hound
80 - Super Bowler
81 - Super Dragon
82 - Headhunter
83 - Super Wizard
84 - Super Minion
95 - Electro Titan
```

## Event troops <a name="2.2"></a>

```
30 - Ice Wizard
45 - Battle Ram
47 - Royal Ghost
48 - Pumpkin Barbarian
50 - Giant Skeleton
61 - Skeleton Barrel
67 - El Primo
72 - Party Wizard
```

## Siege machines <a name="2.3"></a>

```
51 - Wall Wrecker
52 - Battle Blimp
62 - Stone Slammer
75 - Siege Barracks
87 - Log Launcher
91 - Flame Flinger
92 - Battle Drill
```

## Spells <a name="2.4"></a>

```
 0 - Lightning Spell
 1 - Healing Spell
 2 - Rage Spell
 3 - Jump Spell
 5 - Freeze Spell
 9 - Poison Spell
10 - Earthquake Spell
11 - Haste Spell
16 - Clone Spell
17 - Skeleton Spell
28 - Bat Spell
35 - Invisibility Spell
53 - Recall Spell
```

## Event spells <a name="2.1"></a>

```
 4 - Santa's Surprise
22 - Birthday Boom
```