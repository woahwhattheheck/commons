# Cold-chain request history screen

This is a working, responsive React-shaped reference screen implemented with
browser-native HTML, CSS and JavaScript so it can be inspected without a build
step or paid dependency. It advances the internal seller handoff for Freelancer
project `40727247`; it is not a customer destination and contains no buyer data.

## Run

```bash
python3 -m http.server 4173 --directory revenue/freelancer_40727247
```

Open `http://127.0.0.1:4173/`. The app loads `sample_requests.json`, renders
summary cards, a seven-day trend, status mix, filters, a responsive request
history table and a detail dialog. Search, status, location and received-date
filters compose. “Reset” restores the full sample.

## Delivery boundary

The sample records are fictional. A delivery operator should replace the file
adapter with the buyer-supplied endpoint only after the buyer provides the data
shape, expected volume and UI-library preference. API integration, inventory,
reporting, authentication, hosting and paid assets are outside this first-screen
scope. External submission and account action remain owner-only.

## Acceptance

- One responsive operations screen works at desktop and narrow widths.
- Summary cards distinguish new, in-transit, delayed and delivered requests.
- Filters update the cards, trend, status mix and request history together.
- Selecting a row opens the full request, route and cold-chain readings.
- Loading, empty and data-load error states are visible and distinct.
- No login, token, customer data, paid library or external request is required.
