# Event Management

Frappe app for event registration, QR tickets, gate check-in, and organizer reporting.


## Demo Videos

### Organizer Demo

Event setup, ticket types, pricing, capacity, add-ons, and event management.

https://github.com/user-attachments/assets/95eda561-e745-4291-a433-1ec2aa355b2c

### Attendee Demo

Attendee registration, payment status, QR ticket, and PDF ticket download.

https://github.com/user-attachments/assets/e19df72f-1145-42c7-ac0e-5647e4c8ed3e

### Gate Staff Demo

QR-based attendee check-in, duplicate scan handling, and manual check-in.

https://github.com/user-attachments/assets/12c0106d-8ccf-4e8a-a676-38c20d23b139

### Administrator Demo

Administrator dashboard, registrations, revenue, attendance, and reports.

https://github.com/user-attachments/assets/1349733a-04d4-4566-a0b9-bfc86b505a98

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
