#!/usr/bin/env bash
#
# Steam Controller stock checker (standalone version)
# Uses Steam's IStoreBrowseService API — no HTML scraping needed
#
# API returns protobuf: field 3 = availability (0=out of stock, 1=in stock)
# Verified by comparing Steam Deck Dock (in stock, field 3=1) vs
# Steam Controller (out of stock, field 3=0)

NTFY_TOPIC="${NTFY_TOPIC:-steam-controller-stock-checker}"
STEAM_URL="https://store.steampowered.com/hardware/steamcontroller"

# Protobuf-encoded: package 1558609 (Steam Controller), language=english, country=GB
PROTO_INPUT="CNGQXxINCgdlbmdsaXNoGgJHQg=="

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

curl -s -o "$TMPFILE" \
  'https://api.steampowered.com/IStoreBrowseService/GetHardwareItems/v1?origin=https%3A%2F%2Fstore.steampowered.com&input_protobuf_encoded='"$PROTO_INPUT" \
  -H 'Origin: https://store.steampowered.com' \
  -H 'Referer: https://store.steampowered.com/' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' \
  --max-time 15 2>/dev/null

if [ ! -s "$TMPFILE" ]; then
  echo "$(date): Failed to fetch API"
  exit 1
fi

available=$(python3 -c "
import sys
with open(sys.argv[1], 'rb') as f:
    data = f.read()
def decode_varint(data, pos):
    result = shift = 0
    while True:
        b = data[pos]; result |= (b & 0x7f) << shift; pos += 1
        if not (b & 0x80): break
        shift += 7
    return result, pos
pos = 0
tag, pos = decode_varint(data, pos)
length, pos = decode_varint(data, pos)
inner = data[pos:pos+length]
p = 0
fields = {}
while p < len(inner):
    t, p = decode_varint(inner, p)
    fn, wt = t >> 3, t & 7
    if wt == 0:
        v, p = decode_varint(inner, p)
        fields[fn] = v
    else: break
print(fields.get(3, -1))
" "$TMPFILE")

if [ "$available" = "1" ]; then
  echo "$(date): IN STOCK!"
  curl -s \
    -H "Title: Steam Controller IN STOCK!" \
    -H "Priority: urgent" \
    -H "Tags: video_game" \
    -H "Click: $STEAM_URL" \
    -d "The Steam Controller is available for purchase! $STEAM_URL" \
    "https://ntfy.sh/$NTFY_TOPIC"
else
  echo "$(date): Out of stock (availability=$available)"
fi
