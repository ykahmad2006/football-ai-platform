# Football AI Analysis Platform

Milestone 1: football video foundation. Python + FFmpeg, no paid tools.

## Setup (Windows)
1. Install Python 3.11+ and FFmpeg (`winget install Gyan.FFmpeg`)
2. `python -m venv .venv` then `.venv\Scripts\activate`

## Commands
    python -m football_video info match.mp4
    python -m football_video clip match.mp4 --start 00:10:00 --end 00:10:10
    python -m football_video thumbnail match.mp4 --at 00:10:00
    python -m football_video frames match.mp4 --start 00:10:00 --end 00:10:05 --fps 2
    python -m football_video whatsapp clip.mp4
    python -m football_video gif clip.mp4

## Match database (Video -> Match -> Event -> Player -> Clip)
    python -m football_video db init
    python -m football_video match add --home Arsenal --away Liverpool --date 2007-01-06 --competition "FA Cup"
    python -m football_video player add --name "Player Name" --team Arsenal
    python -m football_video video link --match 1 --file match.mp4 --h1 00:01:10 --h2 00:58:30
    python -m football_video event add --match 1 --player 1 --type Goal --period 2 --clock 75:21
    python -m football_video event list --match 1
    python -m football_video event clip 1

## Tests
    python -m unittest discover tests

## Known limits
- Extra time and stoppage-time clocks are not modelled yet
- Event times are typed by hand until event data is imported (next milestone)