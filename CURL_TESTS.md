# AssetFlow – curl Test Commands

> Replace `<ACCESS_TOKEN>` with the JWT obtained from the login step.
> Replace UUIDs (e.g. `<ASSET_ID>`) with real IDs returned by previous responses.

---

## 0. Get tokens (run first)

```bash
# Admin token
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@assetflow.com","password":"Password@123"}' | python -m json.tool

# Manager token
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"manager1@assetflow.com","password":"Password@123"}' | python -m json.tool

# Employee token
curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"emp4@assetflow.com","password":"Password@123"}' | python -m json.tool
```

---

## (a) Allocation Conflict Rejection

**Scenario:** Try to allocate an already-ALLOCATED asset — expect 400 with holder info.

```bash
# Step 1: Get list of assets to find an ALLOCATED one
curl -s http://localhost:8000/api/assets/?status=ALLOCATED \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" | python -m json.tool

# Step 2: Get employee profile IDs
curl -s http://localhost:8000/api/org/employees/ \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" | python -m json.tool

# Step 3: Attempt allocation on an already-ALLOCATED asset
# Replace <ALLOCATED_ASSET_ID> and <ANY_EMPLOYEE_PROFILE_ID>
curl -s -X POST http://localhost:8000/api/allocations/ \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "<ALLOCATED_ASSET_ID>",
    "employee": "<ANY_EMPLOYEE_PROFILE_ID>"
  }' | python -m json.tool

# Expected 400 response:
# {
#   "asset": "Currently held by Grace Employee. Use transfer request instead.",
#   "current_holder_id": "<UUID>"
# }
```

---

## (b) Booking Overlap Rejection

**Scenario:** Book Conference Room A for a time that overlaps an existing booking.
The seed data places booking1 at tomorrow 09:00–11:00 and booking2 at 11:00–13:00.
A booking from 10:00–12:00 overlaps booking1.

```bash
# Step 1: Find the Conference Room A asset ID
curl -s "http://localhost:8000/api/assets/?search=Conference+Room+A" \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" | python -m json.tool

# Step 2: Try to book the overlapping slot (use tomorrow's date)
# Replace <ROOM_A_ASSET_ID> and update the date to tomorrow
curl -s -X POST http://localhost:8000/api/bookings/ \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "asset": "<ROOM_A_ASSET_ID>",
    "start_time": "2026-07-13T10:00:00Z",
    "end_time":   "2026-07-13T12:00:00Z",
    "purpose": "New meeting"
  }' | python -m json.tool

# Expected 400 response:
# {
#   "non_field_errors": "Booking conflicts with an existing booking (2026-07-13T09:00:00Z – 2026-07-13T11:00:00Z).",
#   "conflicting_booking": {
#     "id": "<UUID>",
#     "start_time": "2026-07-13T09:00:00Z",
#     "end_time":   "2026-07-13T11:00:00Z"
#   }
# }
```

---

## (c) Full Transfer Approval Flow (end-to-end)

**Scenario:** emp1 holds a laptop. emp4 wants it. Manager approves the transfer.

```bash
# Step 1: Get emp1's active allocation (contains asset + employee profile IDs)
curl -s "http://localhost:8000/api/allocations/" \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" | python -m json.tool

# Step 2: Get emp4's employee profile ID
curl -s "http://localhost:8000/api/org/employees/?search=emp4" \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" | python -m json.tool

# Step 3: Create a transfer request
# Replace <ASSET_ID>, <EMP1_PROFILE_ID>, <EMP4_PROFILE_ID>
curl -s -X POST http://localhost:8000/api/allocations/transfers/ \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "asset":         "<ASSET_ID>",
    "from_employee": "<EMP1_PROFILE_ID>",
    "to_employee":   "<EMP4_PROFILE_ID>",
    "reason":        "emp4 needs this laptop for the new project"
  }' | python -m json.tool

# Note the "id" in the response — that is <TRANSFER_ID>

# Step 4: Manager approves the transfer
curl -s -X POST "http://localhost:8000/api/allocations/transfers/<TRANSFER_ID>/approve/" \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool

# Expected 200 response:
# {
#   "message": "Transfer approved.",
#   "new_allocation_id": "<UUID>",
#   "transfer_id": "<UUID>"
# }

# Step 5: Verify old allocation is CLOSED and new one is ACTIVE
curl -s "http://localhost:8000/api/allocations/?search=" \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" | python -m json.tool
```

---

## (d) Maintenance Approve → Asset Status Change

**Scenario:** Raise a maintenance request on an AVAILABLE asset, approve it, verify asset becomes UNDER_MAINTENANCE.

```bash
# Step 1: Find an AVAILABLE asset
curl -s "http://localhost:8000/api/assets/?status=AVAILABLE" \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" | python -m json.tool

# Step 2: Raise a maintenance request (any authenticated user)
curl -s -X POST http://localhost:8000/api/maintenance/ \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "asset":       "<AVAILABLE_ASSET_ID>",
    "description": "Power button is stuck",
    "priority":    "HIGH"
  }' | python -m json.tool

# Note the "id" in the response — that is <MAINTENANCE_ID>

# Step 3: Manager approves the request (PENDING → APPROVED; asset → UNDER_MAINTENANCE)
curl -s -X POST "http://localhost:8000/api/maintenance/<MAINTENANCE_ID>/approve/" \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"scheduled_date": "2026-07-20"}' | python -m json.tool

# Expected 200 response:
# {
#   "message": "Maintenance request updated to APPROVED.",
#   "id": "<UUID>",
#   "status": "APPROVED"
# }

# Step 4: Verify the asset status is now UNDER_MAINTENANCE
curl -s "http://localhost:8000/api/assets/<AVAILABLE_ASSET_ID>/" \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" | python -m json.tool

# Expected: "status": "UNDER_MAINTENANCE"

# Step 5: Resolve the request (APPROVED → RESOLVED; asset → AVAILABLE)
curl -s -X POST "http://localhost:8000/api/maintenance/<MAINTENANCE_ID>/resolve/" \
  -H "Authorization: Bearer <MANAGER_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"resolution_notes": "Power button replaced. Asset tested and working."}' | python -m json.tool

# Step 6: Verify asset is AVAILABLE again
curl -s "http://localhost:8000/api/assets/<AVAILABLE_ASSET_ID>/" \
  -H "Authorization: Bearer <EMPLOYEE_ACCESS_TOKEN>" | python -m json.tool
# Expected: "status": "AVAILABLE"
```

---

## Bonus: Swagger UI

Open in browser: http://localhost:8000/api/docs/
