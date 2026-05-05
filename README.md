# Steam Stock Checker

Monitors Steam hardware for stock availability and sends push notifications via [ntfy.sh](https://ntfy.sh) when items become available.

Runs automatically every 5 minutes using GitHub Actions — completely free, no server required.

## Monitored Items

| Item | Check Method |
|------|-------------|
| Steam Controller | Protobuf API (package stock) |
| Steam Frame (VR Headset) | App details (coming soon status) |
| Steam Machine (Console) | App details (coming soon status) |

## How It Works

- Items with a `package_id` are checked via Steam's `IStoreBrowseService/GetHardwareItems` protobuf API — field 3 in the response indicates availability (0 = out of stock, 1 = in stock)
- Items with only an `app_id` (unreleased products) are checked via the `appdetails` API to detect when `coming_soon` flips to `false`
- Notifications are sent via [ntfy.sh](https://ntfy.sh) — install the app on your phone to receive them instantly

## Setup

1. **Fork this repo** (or use it as a template)

2. **Install ntfy** on your phone — [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iOS](https://apps.apple.com/app/ntfy/id1625396347)

3. **Pick a topic name** — something unique like `my-steam-stock-abc123`. Subscribe to it in the ntfy app.

4. **Add the secret** — go to your repo's **Settings → Secrets and variables → Actions** and add:
   - `NTFY_TOPIC` = your chosen topic name

5. **Enable Actions** — go to the **Actions** tab and enable workflows if prompted. The scheduled check will start running every 5 minutes.

6. **Test it** — click **Actions → Steam Hardware Stock Check → Run workflow** to trigger a manual run and verify everything works.

## Adding Items

Edit `items.json` to add or remove items:

```json
[
  {
    "name": "Item Name",
    "app_id": 1234567,
    "package_id": 7654321,
    "url": "https://store.steampowered.com/app/1234567"
  }
]
```

- Set `package_id` for items that have a store package (checks actual stock)
- Set `package_id` to `null` for unreleased items (monitors coming-soon status)

## Running Locally

```bash
# One-off check
NTFY_TOPIC=your-topic python3 check-stock.py

# Or use the shell wrapper
NTFY_TOPIC=your-topic ./check-stock.sh
```

## License

MIT
