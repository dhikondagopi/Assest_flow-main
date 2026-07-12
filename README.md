# AssetFlow Enterprise ERP

AssetFlow Enterprise ERP is a modern enterprise asset management system built for organizations to efficiently manage assets, allocations, maintenance, bookings, audits, notifications, and analytics.

Built for the Odoo Hackathon.

---

## Features

### Dashboard
- Operational overview
- Asset statistics
- Booking summary
- Maintenance overview
- Pending transfers
- Upcoming returns
- Recent activities

### Organization Setup
- Departments
- Categories
- Employees
- User Roles

### Asset Management
- Register Assets
- Edit Assets
- Asset Categories
- Asset Status Tracking
- Department Assignment
- Search & Filters

### Allocation & Transfer
- Allocate Assets
- Transfer Requests
- Duplicate Allocation Protection
- Approval Workflow

### Resource Booking
- Book Meeting Rooms
- Book Shared Resources
- Time Slot Management
- Booking History

### Maintenance
- Raise Maintenance Requests
- Technician Assignment
- Status Tracking
- Resolution History

### Audit
- Audit Cycles
- Asset Verification
- Missing Asset Detection
- Damaged Asset Reports

### Reports
- Asset Utilization
- Department Distribution
- Maintenance Analytics
- Booking Statistics
- CSV Export
- PDF Export

### Notifications
- Real-time Notification Center
- Read / Unread Status
- Category Filters

### Activity Log
- Complete Audit Trail
- User Actions
- Chronological History

---

## Tech Stack

### Frontend

- React 19
- TypeScript
- TanStack Start
- TanStack Router
- TanStack Query
- Tailwind CSS
- shadcn/ui
- Recharts

### Backend

- Supabase
- PostgreSQL
- Row Level Security (RLS)
- SQL Migrations

---

## Project Structure

```
src/
 ├── routes/
 ├── components/
 ├── hooks/
 ├── constants/
 ├── integrations/
 ├── lib/
 └── styles/

supabase/
 ├── migrations/
 └── seed.sql
```

---

## Installation

Clone the repository

```bash
git clone https://github.com/dhikondagopi/Assest_flow-main.git
```

Go to project

```bash
cd Assest_flow-main
```

Install packages

```bash
npm install
```

Start development server

```bash
npm run dev
```

---

## Environment Variables

Create a `.env` file

```env
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_PUBLISHABLE_KEY=your_supabase_anon_key
```

---

## Database

Apply all SQL migrations inside

```
supabase/migrations/
```

Then start the application.

---

## Screens

- Dashboard
- Organization Setup
- Assets
- Allocation & Transfer
- Resource Booking
- Maintenance
- Audit
- Reports
- Notifications
- Activity Log

---

## Future Improvements

- QR Code Asset Tracking
- Barcode Scanner
- Email Notifications
- Mobile Application
- AI Predictive Maintenance
- Real-time Dashboard
- Approval Workflows
- Inventory Forecasting

---

## Contributors

**Dhikonda Gopi**

GitHub

https://github.com/dhikondagopi

---

## License

This project is developed for educational and hackathon purposes.
