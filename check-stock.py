#!/usr/bin/env python3
"""
Steam hardware stock checker.
Reads items.json and checks availability for each item via Steam's APIs.

- Items with package_id: uses IStoreBrowseService/GetHardwareItems protobuf API
- Items with only app_id: uses store API appdetails to detect when coming_soon flips
"""

import base64
import json
import os
import struct
import sys
import urllib.request
import urllib.error


NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "steam-stock-checker")
ITEMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "items.json")

HEADERS = {
    "Origin": "https://store.steampowered.com",
    "Referer": "https://store.steampowered.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
}


def encode_varint(value):
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def decode_varint(data, pos):
    result = shift = 0
    while True:
        b = data[pos]
        result |= (b & 0x7F) << shift
        pos += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def build_protobuf_request(package_id, language="english", country="GB"):
    """Build the protobuf-encoded request for GetHardwareItems."""
    # Field 1 (varint): package_id
    f1 = encode_varint((1 << 3) | 0) + encode_varint(package_id)
    # Field 2 (length-delimited): nested message with language + country
    lang_bytes = language.encode()
    country_bytes = country.encode()
    inner = (encode_varint((1 << 3) | 2) + encode_varint(len(lang_bytes)) + lang_bytes +
             encode_varint((3 << 3) | 2) + encode_varint(len(country_bytes)) + country_bytes)
    f2 = encode_varint((2 << 3) | 2) + encode_varint(len(inner)) + inner
    return base64.b64encode(f1 + f2).decode()


def check_hardware_api(package_id):
    """Check stock via protobuf API. Returns True if in stock, False if not, None on error."""
    proto_input = build_protobuf_request(package_id)
    url = (
        "https://api.steampowered.com/IStoreBrowseService/GetHardwareItems/v1"
        f"?origin=https%3A%2F%2Fstore.steampowered.com&input_protobuf_encoded={proto_input}"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except (urllib.error.URLError, TimeoutError):
        return None

    if not data:
        return None

    try:
        pos = 0
        tag, pos = decode_varint(data, pos)
        length, pos = decode_varint(data, pos)
        inner = data[pos:pos + length]
        p = 0
        fields = {}
        while p < len(inner):
            t, p = decode_varint(inner, p)
            fn, wt = t >> 3, t & 7
            if wt == 0:
                v, p = decode_varint(inner, p)
                fields[fn] = v
            elif wt == 2:
                ln, p = decode_varint(inner, p)
                p += ln
            else:
                break
        availability = fields.get(3, -1)
        return availability == 1
    except (IndexError, ValueError):
        return None


def check_appdetails(app_id):
    """Check via appdetails API. Returns True if no longer coming_soon, False if still coming_soon, None on error."""
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None

    app_data = data.get(str(app_id), {})
    if not app_data.get("success"):
        return None

    release = app_data.get("data", {}).get("release_date", {})
    coming_soon = release.get("coming_soon", True)
    return not coming_soon


def send_notification(item_name, item_url):
    """Send push notification via ntfy.sh."""
    body = f"{item_name} is now available! {item_url}".encode()
    req = urllib.request.Request(f"https://ntfy.sh/{NTFY_TOPIC}", data=body, headers={
        "Title": f"{item_name} IN STOCK!",
        "Priority": "urgent",
        "Tags": "video_game",
        "Click": item_url,
    })
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"  -> Notification sent!")
    except urllib.error.URLError as e:
        print(f"  -> Failed to send notification: {e}")


def main():
    try:
        with open(ITEMS_FILE) as f:
            items = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading {ITEMS_FILE}: {e}")
        sys.exit(1)

    print(f"Checking {len(items)} items...")

    for item in items:
        name = item["name"]
        url = item["url"]
        package_id = item.get("package_id")
        app_id = item.get("app_id")

        print(f"\n{name}:")

        if package_id:
            available = check_hardware_api(package_id)
            if available is None:
                print(f"  API error (package {package_id})")
            elif available:
                print(f"  IN STOCK!")
                send_notification(name, url)
            else:
                print(f"  Out of stock")
        elif app_id:
            available = check_appdetails(app_id)
            if available is None:
                print(f"  API error (app {app_id})")
            elif available:
                print(f"  NOW AVAILABLE (no longer coming soon)!")
                send_notification(name, url)
            else:
                print(f"  Still coming soon")
        else:
            print(f"  Skipped (no package_id or app_id)")


if __name__ == "__main__":
    main()
