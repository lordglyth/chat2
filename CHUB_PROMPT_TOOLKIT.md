# Chub Prompt Toolkit

This project adds a lightweight browser-side prompt toolkit for Chub.ai. It is designed to live on top of the website instead of replacing the app or requiring a backend first.

## Goal

The first release focuses on a modular, editable preset system that can:

- save and load prompt packs
- import and export JSON
- insert prompt modules directly into the active chat input
- toggle optional sections like lore, scene state, commands, and corruption/level systems
- provide a Perplexity-style research prompt bundle for offloaded synthesis
- keep the interface simple enough to work on a mobile Safari workflow later

## Files

- `chub-prompt-toolkit.user.js` — Tampermonkey userscript for Chub.ai
- `chub-prompt-presets.json` — sample preset export to import immediately
- `chat2.html` — earlier browser prototype showing the storage and payload pattern that this project builds on

## Installation

1. Install a userscript manager such as Tampermonkey or Violentmonkey.
2. Open `chub-prompt-toolkit.user.js` in the browser and install it.
3. Browse to `https://chub.ai/*`.
4. A floating panel should appear in the upper-right corner of the page.

## Using presets

The panel includes:

- active preset preview
- insert active pack into the current chat composer
- export JSON
- import JSON
- list of preset cards with Activate and Insert buttons

The default preset categories include:

- preprompt
- impersonation
- scene
- commands
- level/status system
- research / connector stack
- output format

## Importing the sample preset pack

Use the JSON in `chub-prompt-presets.json` by pasting it into the import textarea and clicking `Import JSON`.

## Perplexity research pack

The bundled `perplexity-research` preset is designed to handle research and offload work into a reusable workflow:

- source gathering
- GitHub / Notion / Context7 / Perplexity input
- fact comparison and synthesis
- final output plus reusable prompt or lore block

Suggested command flow:

1. Pull relevant documents or notes.
2. Add the research preset to the chat.
3. Ask the model to compare sources, identify contradictions, and summarize the cleanest output.
4. Ask for an exportable prompt block or lorebook update.

## Modular configuration model

Each preset is defined as a JSON object containing:

```
{
  "id": "preset-id",
  "name": "Preset Name",
  "description": "Short description",
  "modules": [
    {
      "id": "module-id",
      "category": "preprompt",
      "enabled": true,
      "name": "Module Name",
      "content": "Text inserted when the module is enabled."
    }
  ]
}
```

This structure is intentionally simple so it can later support:

- per-character memory
- global prompt packs
- lorebook entries
- scene states
- skill toggles
- importers from Notion, GitHub, or plaintext notes

## Useful connectors to extend later

These are the most relevant to this direction:

- GitHub: store reusable prompt packs and version them in repo files
- Notion: keep worldbuilding, lore, and prompt docs in a shared workspace
- Context7: citation and reference retrieval for grounded prompts
- Perplexity: external fact-finding and comparison layer
- Supabase: syncable shared preset library
- Dropbox / Google Drive: backup and migration path

Lower priority for the first milestone:

- ParseHub
- DataForSEO
- Semrush
- CloudConvert
- WebScraping.AI
- Google Photos
- Jam

These can be useful later for scraping research or bulk content conversion, but they are not required for the basic modular foundation.

## Mobile Safari note

This is a desktop-first userscript by design. Full userscript support is not reliable on iPhone Safari. The realistic path for mobile is to keep the preset format and prompt schema portable, then later wrap the same logic in a Safari-friendly web app or PWA with the same JSON-driven system.

## Design notes

This project focuses on the smallest viable foundation:

- modular prompt blocks
- prompt pack export/import
- live insert into the current chat
- clear storage and configuration
- a built-in research workflow

That gives a clean foundation for future expansion into custom connectors, external sync, and richer prompt generation without locking the project into a single app architecture.
