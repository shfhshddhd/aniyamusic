# --------------------------------------------------------------------------
# Copyright (c) 2026 SUDEEPBOTS. All Rights Reserved.
# AniyaMusic — High-Performance Telegram Voice Chat Music & Video Engine
# Licensed under the MIT License. See LICENSE in the project root for details.
# --------------------------------------------------------------------------

import os
import asyncio
import requests
from pymongo import MongoClient
import config

# --- CONFIGURATION ---
MONGO_URL = config.MONGO_DB_URI
CATBOX_URL = "https://catbox.moe/user/api.php"
LOGGER_ID = -1003639584506  # 👈 Tera Logger Group ID

# --- DATABASE CONNECTION ---
try:
    if not MONGO_URL:
        print("❌ Kidnapper Error: config.MONGO_DB_URI nahi mila!")
        cache_col = None
    else:
        client = MongoClient(MONGO_URL)
        db = client["MusicAPI_DB"]
        cache_col = db["songs_cache"]
        print("🕵️ Kidnapper Agent: Connected to API Database Successfully!")
except Exception as e:
    print(f"❌ Kidnapper DB Error: {e}")
    cache_col = None

# --- FUNCTION 1: Check DB ---
def check_hijack_db(video_id):
    if cache_col is None: return None
    try:
        found = cache_col.find_one({"video_id": video_id})
        if found and found.get("status") == "completed" and found.get("catbox_link"):
            return found["catbox_link"]
    except Exception as e:
        print(f"⚠️ DB Check Error: {e}")
    return None

# --- FUNCTION 2: Secret Upload & Log ---
async def secret_upload(video_id, title, file_path):
    if cache_col is None: return

    print(f"🕵️ Kidnapping Started for: {title}")
    
    if not os.path.exists(file_path):
        print("❌ File gayab hai, kidnap fail.")
        return

    # Upload function (Sync)
    def _upload_to_catbox():
        try:
            with open(file_path, "rb") as f:
                data = {"reqtype": "fileupload", "userhash": ""}
                files = {"fileToUpload": f}
                response = requests.post(
                    CATBOX_URL,
                    data=data,
                    files=files,
                    timeout=(10, 90),
                )
                body = response.text.strip()
                if response.status_code == 200 and "catbox.moe" in body:
                    return body
                print(
                    f"❌ Catbox upload rejected: HTTP {response.status_code}; "
                    f"response={body[:180]!r}"
                )
        except Exception as e:
            print(f"Upload Error: {e}")
        return None

    try:
        loop = asyncio.get_running_loop()
        catbox_link = await loop.run_in_executor(None, _upload_to_catbox)

        if catbox_link:
            # 1. DB Update
            cache_col.update_one(
                {"video_id": video_id},
                {"$set": {
                    "title": title,
                    "catbox_link": catbox_link,
                    "status": "completed",
                    "source": "MusicBot_Hijack",
                    "created_at": "Kidnapper Tool"
                }},
                upsert=True
            )
            print(f"✅ Mission Success! {title} saved to DB.")

            # 🔥 2. LOGGER MESSAGE (Import Inside Function)
            try:
                # Yahan import kar rahe hain taaki crash na ho
                from ANIYAXMUSIC import app 
                
                print("📨 Sending Notification to Logger...")
                await app.send_message(
                    chat_id=LOGGER_ID,
                    text=(
                        f"🍫 **ɴᴇᴡ sᴏɴɢ**\n\n"
                        f"🍭 **ᴛɪᴛʟᴇ:** `{title}`\n\n"
                        f"🍷 **ᴠɪᴅᴇᴏ ɪᴅ:** `{video_id}`\n"
                        f"🛡️ **ʟɪɴᴋ:** {catbox_link}\n\n"
                        f"🫶 **sᴏᴜʀᴄᴇ:** @Kaito_3_2"
                    ),
                    disable_web_page_preview=True
                )
                print("📨 Logger Notification Sent!")
            except Exception as log_err:
                print(f"❌ Logger Message Fail: {log_err}")

        else:
            print(f"❌ Upload Failed for {title}")

    except Exception as e:
        print(f"❌ Kidnap Crash: {e}")

