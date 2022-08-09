# Clash API Developers - How to run your bot 24/7
## Table of Content
1. [Need to run your bot 24/7?](#1)
2. [Using Local Hardware](#2)
3. [Using a VPS](#3)
4. [Specialty VPS (Like Heroku)](#4)
5. [Linux and Workflows](#5)



## Need to run your bot 24/7? <a name="1"></a>
So you have found yourself needing to run your discord bot for long periods of time, eh? A simple solution is using the computer that you developed your bot in. You can keep that computer running indefinitely and the bot will keep on trucking along. 
That's not ideal? No problem, there are other solutions. The two types of solutions are, using local hardware or renting server space or "VPS

## Using Local hardware <a name="2"></a>
Local hardware can be any computer. Discord bots are generally lightweight unless you start writing and reading from a massive database and start servicing hundreds of users. With that in mind, an old PC or laptop can be repurposed to run your discord bot. If the hardware is super old, 
you can install a lightweight operating system to alleviate some of the hardware constraints. 

One of the most used operating systems for this type of work is a Linux Distribution. Linux can be a bit daunting at first, 
but if you stick with a user-friendly distribution like Ubuntu, then you will have nothing to worry about. Ubuntu has tons of resources
online if you end up getting stuck. We highly recommend [Xubuntu](https://xubuntu.org). It has an ugly/lightweight desktop environment so that all your resources can be used where it counts, your bot. 

Alternatively to old hardware, is buying new hardware. You can even get away with a [raspberry pi](https://www.raspberrypi.org/products/raspberry-pi-4-model-b/). 
You can pick one up for as little as $35. They also come with fantastic resources like learning how to use Linux. 

## Using a VPS <a name="3"></a>
VPS is short for a virtual private server. A VPS is essentially a logically distributed hardware using some kind of virtualization software. 
In other words, a company buys a big server and uses some virtualization software to divide up their server into smaller chunks and assign the user a piece. 

But all that stuff is hidden from you. To you, it's just another computer that you are renting for a monthly price. With that said, some 
of the top recommended sites are as follow:

| Site | Based | Description|
| --- | --- | --- |
| [Linode](https://www.linode.com/) | US | One of the oldest providers, a pioneer in this space. They are even older than AWS. If you like supporting open source communities, then you should get your VPS from them as they constanly support open source projects |
| [Scaleway](https://www.scaleway.com/) | EU | Incredibly cheap but powerful VPSes |
| [DigitalOcean](https://www.digitalocean.com/) | US | Top tier service with indepth writeups on things like setting up services. If not for their VPS at least checkout their write ups |
| [AWS](https://aws.amazon.com) | US | The biggest player in the VPS space. So big that they have even created their own CLI and Linux distribution. If you plan on working for a big company it will not be a bad idea to at least use AWS for their free 1 year tier |
| [Azure](https://azure.microsoft.com/en-us/) | US | Same as AWS. They also offer a free tier for a year that you can take advantage of |
| [Google Cloud](https://cloud.google.com) | US | Same as AWS. They also offer up to $300 worth of credit to use on ther services |
| [time4vps](https://www.time4vps.eu/) | EU | Cheap VPSes, seemingly based in Lithuania. |
| [netcup](https://www.netcup.eu/vserver/vps.php) | EU | Based in Germany, very reliable |
| [GalaxyGate](https://galaxygate.net/) | US | A big takeaway on this one is their great Linux guide for setting up a [discord bot systemd service](https://wiki.galaxygate.net/hosting/discord/python/) |


## Specialty VPS (Like Heroku) <a name="4"></a>
With a VPS you usually have a decent amount of control. Meaning that it is up to you to install the software you need to run your code and it is also up to you to secure your server from the internet. 

There are other types of VPS's that attempt to abstract that from you by providing an interface where you do not have to worry about OS-level configurations. These types of VPS's include things like [Heroku](https://www.heroku.com) and [replit](https://replit.com/languages/python3)

These are generally fine for development, but a word of caution. Because of the tight control, some of the traffic could be proxied which could cause issues when your bot is interacting with other APIs. 


## Linux and workflow <a name="5"></a>
If you end up choosing a VPS as an option, it will often require you to learn Linux. Linux is the operating system of the internet, most servers run on 
Linux. For this reason, it's highly encouraged that you take the time and learn how to use Linux while attempting to configure your bots. 

A few things to keep in mind. With a VPS, there is a good chance that you will only have a terminal to communicate with the server. We highly 
encourage you to use the [Raspberry Pi](https://www.raspberrypi.org/documentation/computers/using_linux.html) documentation on basic Linux commands. 
Keep in mind that the Raspberry Pi base image is Debian, so if you are using a distribution that is not Debian-based such as Ubuntu, PopOS, and Mint then some of the commands may not work. Especially the package commands (apt vs yum vs pacman).

Another thing to consider when using a Linux VPS is how to keep your program running. Most modern Linux systems run on what's called "SystemD". SystemD controls what starts and stops when the operating system starts. You can register your application with the SystemD so that it too can run when the operating system starts. [GalaxyGate](https://wiki.galaxygate.net/hosting/discord/python/) has a nice writeup on how to set this up!

> Pro tip! If you want to see your logs from the system d you can use the following commands.
```bash
journalctl -f --unit=<bot_service>
```

A final note. It may be confusing figuring out how to get your code onto the VPS server. Ideally, you should be developing on a local machine with your pretty GUI, IDE, and music. Once your code is fully tested and functioning, you should push it with git. Then you log into your VPS and you git pull the changes and re-run your bot. This will keep your VPS running at all times and will not get corrupted by you accidentally making changes. 

An example of a workflow may look like this:
```bash
# On your local machine
## Checkout a new branch, never code on main branch!
git checkout -b adding_button_feature
git add .
git commit -m "Added new button feature! Fully tested and ready to deploy"
## Push the new changes and merge to maind
git push origin adding_button_feature
git switch main
git merge adding_button_feature --no-ff -m "Merging tested feature to main branch"

# On remote machine
git pull origin main
systemctl restart <bot>
```
