# Event Management

Frappe app for event registration, QR tickets, gate check-in, and organizer reporting.

## Setup

```bash
# Install app into your bench
cd frappe-bench
bench get-app /path/to/event_management   # or clone into apps/
bench --site your-site install-app event_management

# Build attendee portal
cd apps/event_management/frontend
yarn && yarn build
cd ../../..
bench build --app event_management
bench --site your-site clear-cache

# Demo data (optional)
bench --site your-site execute event_management.seed_devcon.run
```

Portal: `/em/events` · Desk: search **EM Event**

## Tests

```bash
bench --site your-site set-config allow_tests true
bench --site your-site run-tests --app event_management
```

## Roles

| Role | Access |
|------|--------|
| Event Organizer | Desk + dashboard APIs |
| Event Gate Staff | Scanner / check-in |
| Event Attendee | Portal only |

## Payments

Free tickets confirm immediately. Paid tickets use Razorpay when configured:

```json
{ "razorpay_key_id": "...", "razorpay_key_secret": "..." }
```

Without gateway keys, use **Pay Now** on the registration page (requires `developer_mode`).

## License

MIT
