# Gairedzi Client Dashboard (Angular)

This Angular app presents the project JSON inputs in a client-friendly website.

## What it shows

- Selectable list of data files from `public/data/`
- Structural summary for each JSON file:
  - root type
  - object key count
  - array node count
  - primitive value count
  - maximum depth
- Full formatted JSON viewer

## Data source

Data files are copied from the repository `Data/` folder into:

- `client-dashboard/public/data/`

## Run locally

From the repository root:

```bash
cd client-dashboard
npm install
npm start
```

Then open the URL shown in terminal (typically http://localhost:4200).

## Build

```bash
cd client-dashboard
npm run build
```

If build crashes on macOS with a Node/esbuild error, switch to Node 20 or 22 LTS and retry.
