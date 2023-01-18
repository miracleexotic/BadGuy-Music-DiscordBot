# BadGuy 🎶
## _The discord music bot._

- Type some Command on the message box start with `>`
- _Not implement with `/` command at this moment_

## Features

- Search/Play music from youtube with [youtube-dl](https://github.com/ytdl-org/youtube-dl).
- Play music from spotify playlist.

#### :: Mode ::
- ##### Normal
    Play song in queue.
- ##### Loop
    Loop current song.
- ##### History Loop
    Loop all song in history.
- ##### Spotify
    Play song from spotify playlist.

##### TODO
- ##### Autoplay
    Play next song without request from user.

## Tech

- [Discord.py](https://github.com/Rapptz/discord.py) - A modern, easy to use, feature-rich, and async ready API wrapper for Discord written in Python.
- [youtube-dl](https://github.com/ytdl-org/youtube-dl) - download videos from youtube.com or other video platforms.
- [ffmpeg](https://ffmpeg.org/) - A complete, cross-platform solution to record, convert and stream audio and video.

## Installation

BadGuy requires [Python](https://www.python.org/) v3.10.4+ to run.

#### Git clone
```sh
git clone https://github.com/miracleexotic/BadGuy-Music-DiscordBot.git
cd BadGuy-Music-DiscordBot
```

#### Pre-Deploy and Pre-Run
First, Need to **create** `authentication` folder in `BadGuy-Music-DiscordBot` folder.
```sh
mkdir -p authentication
cd authentication
nano config.json
```
Write this below code in `config.json` and replace your **key** in `<KEY: Description>`
```
{
    "README": "Make a duplicate of this file and save it as config.json. Then configure the bot however you want",
    "token" : "<KEY: Discord bot token>",
    "spotify": {
        "cid": "<KEY: spotify cid>",
        "secret": "<KEY: spotify secret>"
    }
}
```

#### PIP
Install the dependencies and devDependencies.
```sh
pip install -r requirements.txt
```

#### run
```sh
python main.py
```

## Docker

BadGuy is very easy to install and deploy in a Docker container.

```sh
cd BadGuy-Music-DiscordBot
docker build -t <youruser>/badguy-music-discord .
```

This will create the dillinger image and pull in the necessary dependencies.

Once done, run the Docker image:

```sh
docker run -d --name=badguy <youruser>/badguy-music-discord
```

## License

MIT

**Free Software, Hell Yeah!**
