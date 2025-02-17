import io
import os
import re
import shutil
import tempfile
import datetime

from yt_dlp import YoutubeDL
from pyrogram.helpers import ikb
from pyrogram import Client, filters
from pyrogram.errors import BadRequest
from pyrogram.types import CallbackQuery, Message

from ..config import prefix
from ..utils.localization import use_chat_lang
from ..utils import aiowrap, http, pretty_size, commands


YOUTUBE_REGEX = re.compile(
    r"(?m)http(?:s?):\/\/(?:www\.)?(?:music\.)?youtu(?:be\.com\/(watch\?v=|shorts/)|\.be\/|)([\w\-\_]*)(&(amp;)?[\w\?=]*)?"
)

TIME_REGEX = re.compile(r"[?&]t=([0-9]+)")

MAX_FILESIZE = 200000000


@aiowrap
def extract_info(instance: YoutubeDL, url: str, download=True):
    return instance.extract_info(url, download)


async def search_yt(query):
    page = (
        await http.get(
            "https://www.youtube.com/results",
            params=dict(search_query=query, pbj="1"),
            headers={
                "x-youtube-client-name": "1",
                "x-youtube-client-version": "2.20200827",
            },
        )
    ).json()
    list_videos = []
    for video in page[1]["response"]["contents"]["twoColumnSearchResultsRenderer"][
        "primaryContents"
    ]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]:
        if video.get("videoRenderer"):
            dic = {
                "title": video["videoRenderer"]["title"]["runs"][0]["text"],
                "url": "https://www.youtube.com/watch?v="
                + video["videoRenderer"]["videoId"],
            }
            list_videos.append(dic)
    return list_videos


@Client.on_message(filters.command(["yt", "search"], prefix))
@use_chat_lang()
async def yt_search_cmd(c: Client, m: Message, strings):
    if len(m.command) < 2:
        await m.reply_text(strings("youtube_search_usage"))
    else:
        vids = [
            '{}: <a href="{}">{}</a>'.format(num + 1, i["url"], i["title"])
            for num, i in enumerate(await search_yt(m.text.split(None, 1)[1]))
        ]
        await m.reply_text(
            "\n".join(vids) if vids else r"¯\_(ツ)_/¯", disable_web_page_preview=True
        )


@Client.on_message(filters.command(["ytdl", "download", "song", "video"], prefix))
@use_chat_lang()
async def ytdlcmd(c: Client, m: Message, strings):
    user = m.from_user.id
    
    afsize = 0
    vfsize = 0

    if len(m.command) < 2:
        return await m.reply_text(strings("youtube_download_usage"))
    if m.reply_to_message and m.reply_to_message.text:
        url = m.reply_to_message.text
    elif len(m.command) > 1:
        url = m.text.split(None, 1)[1]
    else:
        await m.reply_text(strings("ytdl_missing_argument"))
        return

    ydl = YoutubeDL({"noplaylist": True})
    match = YOUTUBE_REGEX.match(url)

    t = TIME_REGEX.search(url)
    temp = t.group(1) if t else 0

    if match:
        yt = await extract_info(ydl, match.group(), download=False)
    else:
        yt = await extract_info(ydl, "ytsearch:" + url, download=False)
        yt = yt["entries"][0]

    for f in yt["formats"]:
        if f["format_id"] == "140":
            afsize = f["filesize"] or 0
        if f["ext"] == "mp4" and f["filesize"] is not None:
            vfsize = f["filesize"] or 0
            vformat = f["format_id"]

    keyboard = [
        [
            (
                strings("ytdl_audio_button"),
                f'_aud.{yt["id"]}|{afsize}|{temp}|{m.chat.id}|{user}|{m.id}',
            ),
            (
                strings("ytdl_video_button"),
                f'_vid.{yt["id"]}|{vfsize}|{temp}|{m.chat.id}|{user}|{m.id}',
            ),
        ]
    ]

    if " - " in yt["title"]:
        performer, title = yt["title"].rsplit(" - ", 1)
    else:
        performer = yt.get("creator") or yt.get("uploader")
        title = yt["title"]

    text = f"🎧 <b>{performer}</b> - <i>{title}</i>\n"
    text += f"🗂 <code>{pretty_size(afsize)}</code> (audio) / <code>{pretty_size(int(vfsize))}</code> (video)\n"
    text += f"⏳ <code>{datetime.timedelta(seconds=yt.get('duration'))}</code>"

    await m.reply_text(text, reply_markup=ikb(keyboard))


@Client.on_callback_query(filters.regex("^(_(vid|aud))"))
@use_chat_lang()
async def cli_ytdl(c: Client, cq: CallbackQuery, strings):
    data, fsize, temp, cid, userid, mid = cq.data.split("|")
    if not cq.from_user.id == int(userid):
        return await cq.answer(strings("ytdl_button_denied"), cache_time=60)
    if int(fsize) > MAX_FILESIZE:
        return await cq.answer(
            strings("ytdl_file_too_big"),
            show_alert=True,
            cache_time=60,
        )
    vid = re.sub(r"^\_(vid|aud)\.", "", data)
    url = "https://www.youtube.com/watch?v=" + vid
    await cq.message.edit(strings("ytdl_downloading"))
    with tempfile.TemporaryDirectory() as tempdir:
        path = os.path.join(tempdir, "ytdl")

    ttemp = ""
    if int(temp):
        ttemp = f"⏰ {datetime.timedelta(seconds=int(temp))} | "

    if "vid" in data:
        ydl = YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": "best[ext=mp4]",
                "max_filesize": MAX_FILESIZE,
                "noplaylist": True,
            }
        )
    else:
        ydl = YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": "bestaudio[ext=m4a]",
                "max_filesize": MAX_FILESIZE,
                "noplaylist": True,
            }
        )
    try:
        yt = await extract_info(ydl, url, download=True)
    except Exception as e:
        await cq.message.edit(strings("ytdl_send_error").format(errmsg=e))
        return
    await cq.message.edit(strings("ytdl_sending"))
    filename = ydl.prepare_filename(yt)
    thumb = io.BytesIO((await http.get(yt["thumbnail"])).content)
    thumb.name = "thumbnail.png"
    try:
        if "vid" in data:
            await c.send_video(
                int(cid),
                filename,
                thumb=thumb,
                caption=ttemp + yt["title"],
                duration=yt["duration"],
                reply_to_message_id=int(mid),
            )
        else:
            if " - " in yt["title"]:
                performer, title = yt["title"].rsplit(" - ", 1)
            else:
                performer = yt.get("creator") or yt.get("uploader")
                title = yt["title"]
            await c.send_audio(
                int(cid),
                filename,
                title=title,
                thumb=thumb,
                performer=performer,
                caption=ttemp[:-2],
                duration=yt["duration"],
                reply_to_message_id=int(mid),
            )
    except BadRequest as e:
        await cq.message.edit_text(strings("ytdl_send_error").format(errmsg=e))
    else:
        await cq.message.delete()

    shutil.rmtree(tempdir, ignore_errors=True)


commands.add_command("search", "general")
commands.add_command("download", "general")
