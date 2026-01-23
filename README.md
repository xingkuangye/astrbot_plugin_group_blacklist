# astrbot-plugin-group-blacklist

A small Astrbot plugin to ignore or block messages from specified group IDs.

## Features
- Maintain a list of blacklisted group IDs
- Ignore incoming messages from blacklisted groups
- Simple JSON config for persistence

## Installation
1. Copy the plugin folder to Astrbot's `plugins/` directory.
2. Add or update plugin entry in Astrbot config and restart the bot.

## Configuration (example)
Place a config file `group_blacklist.json` or merge into bot config:
```json
{
    "enabled": true,
    "blacklist": [
        "1234567890",
        "9876543210"
    ],
    "mode": "ignore" // or "block"
}
```

## Usage
- The plugin will automatically ignore messages from any group whose ID appears in the `blacklist`.
- Optionally provide management commands (if implemented by this plugin):
    - `!gblist` — show blacklisted group IDs
    - `!gbadd <group_id>` — add a group to the blacklist
    - `!gbremove <group_id>` — remove a group from the blacklist

## Contributing
Open an issue or PR with improvements or bug fixes.
