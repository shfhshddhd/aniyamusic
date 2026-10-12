# --------------------------------------------------------------------------
# Copyright (c) 2026 SUDEEPBOTS. All Rights Reserved.
# AniyaMusic — High-Performance Telegram Voice Chat Music & Video Engine
# Licensed under the MIT License. See LICENSE in the project root for details.
# --------------------------------------------------------------------------

import asyncio
import os
import re
import aiohttp
import json
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from ANIYAXMUSIC.utils.database import is_on_off
from ANIYAXMUSIC.utils.formatters import time_to_seconds

# SHRUTI API CONFIG
FALLBACK_API_URL = "https://shrutibots.site"
YOUR_API_URL = None
cookies_file = "ANIYAXMUSIC/assets/cookies.txt"


async def get_api_url():
    global YOUR_API_URL
    if YOUR_API_URL:
        return YOUR_API_URL
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://pastebin.com/raw/rLsBhAQa", timeout=5) as resp:
                if resp.status == 200:
                    YOUR_API_URL = (await resp.text()).strip()
                else:
                    YOUR_API_URL = FALLBACK_API_URL
    except Exception:
        YOUR_API_URL = FALLBACK_API_URL
    return YOUR_API_URL


async def download_via_shruti(link: str, is_video: bool = False):
    api_url = await get_api_url()
    video_id = link.split('v=')[-1].split('&')[0] if 'v=' in link else link
    os.makedirs("downloads", exist_ok=True)
    ext = "mp4" if is_video else "mp3"
    file_path = os.path.join("downloads", f"{video_id}.{ext}")
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    try:
        async with aiohttp.ClientSession() as session:
            req_type = "video" if is_video else "audio"
            async with session.get(
                f"{api_url}/download",
                params={"url": video_id, "type": req_type},
                timeout=20,
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                token = data.get("download_token")
                if not token:
                    return None

            stream_url = f"{api_url}/stream/{video_id}?type={req_type}"
            async with session.get(
                stream_url,
                headers={"X-Download-Token": token},
                timeout=600,
            ) as resp:
                if resp.status != 200:
                    return None
                with open(file_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(16384):
                        f.write(chunk)
                return file_path if os.path.exists(file_path) and os.path.getsize(file_path) > 0 else None
    except Exception as e:
        print(f"Shruti API download failed ({type(e).__name__}); trying yt-dlp fallback.")
        return None


async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in errorz.decode("utf-8", errors="replace").lower():
            return out.decode("utf-8", errors="replace")
        return errorz.decode("utf-8", errors="replace")
    return out.decode("utf-8", errors="replace")


class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset is not None:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset is None:
            return None
        return text[offset:offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = 0 if str(duration_min) == "None" else int(time_to_seconds(duration_min))
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["thumbnails"][0]["url"].split("?")[0]

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await shell_cmd(
            f'yt-dlp --cookies "{cookies_file}" -i --get-id --flat-playlist --playlist-end {int(limit)} --skip-download "{link}"'
        )
        return [key for key in playlist.splitlines() if key and not key.startswith("ERROR:")]

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title, "link": yturl, "vidid": vidid,
            "duration_min": duration_min, "thumb": thumbnail
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {
            "quiet": True,
            "no_warnings": True,
            "cookiefile": cookies_file,
            "format": "bestaudio/best",
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            formats_available = []
            for fmt in info.get("formats", []):
                try:
                    if "dash" not in str(fmt.get("format", "")).lower():
                        formats_available.append({
                            "format": fmt.get("format"),
                            "filesize": fmt.get("filesize"),
                            "format_id": fmt.get("format_id"),
                            "ext": fmt.get("ext"),
                            "format_note": fmt.get("format_note"),
                            "yturl": link,
                        })
                except Exception:
                    continue
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        is_video_req = bool(video or songvideo)

        try:
            downloaded_file = await download_via_shruti(link, is_video=is_video_req)
            if downloaded_file:
                return downloaded_file, True
        except Exception as e:
            print(f"Shruti API failed ({type(e).__name__}); trying yt-dlp fallback.")

        loop = asyncio.get_running_loop()

        def download_with_ytdlp(options):
            os.makedirs("downloads", exist_ok=True)
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(link, download=False)
                video_id = info.get("id", "youtube_download")
                ext = info.get("ext", "m4a")
                output_path = os.path.join("downloads", f"{video_id}.{ext}")
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    return output_path
                ydl.download([link])
                # Use actual final file if yt-dlp changed the extension/container.
                for candidate in (
                    os.path.join("downloads", f"{video_id}.{ext}"),
                    os.path.join("downloads", f"{video_id}.m4a"),
                    os.path.join("downloads", f"{video_id}.webm"),
                    os.path.join("downloads", f"{video_id}.mp4"),
                    os.path.join("downloads", f"{video_id}.mp3"),
                ):
                    if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                        return candidate
                raise FileNotFoundError("yt-dlp reported success but no output file was found")

        common = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "cookiefile": cookies_file,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": False,
            "retries": 3,
            "fragment_retries": 3,
        }
        if is_video_req:
            options = {
                **common,
                # Prefer MP4 streams, but fall back to any available video/audio format.
                "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/bestvideo*+bestaudio/best",
                "merge_output_format": "mp4",
            }
        else:
            options = {
                **common,
                # Try audio-only first, then a muxed format if YouTube exposes no audio-only formats.
                "format": "bestaudio/best",
            }
        downloaded_file = await loop.run_in_executor(None, download_with_ytdlp, options)
        return downloaded_file, True
