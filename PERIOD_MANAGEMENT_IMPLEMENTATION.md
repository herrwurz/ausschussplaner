# Period Management Admin Implementation

## Overview

Complete admin period (Gemeinderatsperiode) management has been implemented with the following features:
- Period listing, creation, editing, and deletion
- Person assignment to periods with automatic membership cleanup
- Committee management within periods
- Automatic Jahresplan variante creation when personnel changes
- Quorum calculation based on membership changes

## Implementation Summary

### 1. Helper Function: `calculate_quorum(member_count)`

**Location:** `app/api/routes/admin.py` (lines 61-67)

```python
def calculate_quorum(member_count: int) -> int:
    """Calculate quorum as 50% of members + Obmann must be present.
    
    Returns: ceil(total_members / 2) — minimum members needed for quorum.
    Obmann is mandatory (separate requirement).
    """
    return ceil(member_count / 2)
```

**Formula:** `ceil(total_members / 2)`
- Example: 6 members → quorum = 3 (50% + 1)
- Example: 7 members → quorum = 4 (50% + 1)
- Used when removing persons from periods to recalculate ausschuss requirements

---

## Admin Routes

All routes require `is_logged_in()` check and follow HTTP REST conventions.

### Period Listing & Management

#### 1. GET `/admin/perioden`
**Handler:** `perioden_list()`
**Response:** Jinja2 template `perioden.html`

Displays all periods with:
- Period name and timeframe (start_jahr – end_jahr)
- Active/Inactive status badge
- Person count (active members only)
- Committee count
- Action buttons: Detail, Edit, Delete

Data aggregation:
```python
periode_persons_count = {}
periode_committees_count = {}
for periode in perioden:
    person_count = db.query(PeriodePerson).filter(
        PeriodePerson.periode_id == periode.id,
        PeriodePerson.end_datum.is_(None)
    ).count()
    committee_count = db.query(Ausschuss).filter(
        Ausschuss.periode_id == periode.id
    ).count()
```

---

#### 2. GET `/admin/perioden/create`
**Handler:** `perioden_create_form()`
**Response:** HTML form

Form fields:
- `name` (String, required) - e.g., "P1"
- `start_jahr` (Integer, required)
- `end_jahr` (Integer, required)
- `aktiv` (Checkbox)

---

#### 3. POST `/admin/perioden/create`
**Handler:** `perioden_create()`
**Validation:**
- name must not be empty
- start_jahr ≤ end_jahr
- name must be unique (IntegrityError on duplicate)

**Result:** Redirect to `/admin/perioden`

---

#### 4. GET `/admin/perioden/{periode_id}`
**Handler:** `periode_detail()`
**Response:** Jinja2 template `periode_detail.html`

Two-column layout:

**Left Column: Persons**
- List of active members (end_datum IS NULL)
- Form to add new persons (dropdown, date auto-filled to today)
- Remove button triggers new Jahresplan variante creation

**Right Column: Committees**
- List of ausschuesse with member counts
- Typ badge (standard/poly/kontroll)
- Link to manage memberships
- Button to add new committee

Data prepared:
```python
periode_personen = db.query(PeriodePerson).filter(
    PeriodePerson.periode_id == periode_id,
    PeriodePerson.end_datum.is_(None)
).all()

ausschuesse = db.query(Ausschuss).filter(
    Ausschuss.periode_id == periode_id
).all()

available_persons = db.query(Person).filter(
    Person.aktiv == True,
    ~Person.id.in_(existing_person_ids)
).order_by(Person.nachname).all()
```

---

#### 5. POST `/admin/perioden/{periode_id}/person-add`
**Handler:** `periode_person_add()`

**Form Field:** `person_id` (required)

**Validation:**
- person_id must be valid
- Person must not already be in period (check end_datum IS NULL)

**Action:** Creates `PeriodePerson` record:
```python
periode_person = PeriodePerson(
    periode_id=periode_id,
    person_id=person_id,
    start_datum=date.today()
)
```

**Result:** Redirect to period detail page

---

#### 6. GET `/admin/perioden/{periode_id}/person/{person_id}/remove`
**Handler:** `periode_person_remove()`

**Critical Logic - Two-Phase Update:**

**Phase 1: Mark Person as Removed**
```python
periode_person = db.query(PeriodePerson).filter(
    PeriodePerson.periode_id == periode_id,
    PeriodePerson.person_id == person_id,
    PeriodePerson.end_datum.is_(None)
).first()

if periode_person:
    periode_person.end_datum = date.today()
    periode_person.grund_austritt = "Aus Periode entfernt"
```

**Phase 2: Remove All Memberships & Update Quorum**
```python
# 1. Remove all Mitgliedschaft records for this person in period
memberships_to_remove = db.query(Mitgliedschaft).filter(
    Mitgliedschaft.periode_id == periode_id,
    Mitgliedschaft.person_id == person_id
).all()

affected_ausschuesse_ids = set()
for membership in memberships_to_remove:
    affected_ausschuesse_ids.add(membership.ausschuss_id)
    db.delete(membership)

# 2. Create new Jahresplan variante
latest_jahresplan = db.query(Jahresplan).filter(
    Jahresplan.periode_id == periode_id,
    Jahresplan.jahr == current_year
).order_by(Jahresplan.variante.desc()).first()

if latest_jahresplan:
    new_variante = latest_jahresplan.variante + 1
    new_jahresplan = Jahresplan(
        periode_id=periode_id,
        jahr=current_year,
        variante=new_variante,
        grund_variante=f"Austritt {person_name_str} - Quorum-Update erforderlich",
        aktiv=True
    )
    db.add(new_jahresplan)

# 3. Recalculate quorum for affected committees
for ausschuss_id in affected_ausschuesse_ids:
    ausschuss = db.query(Ausschuss).filter(
        Ausschuss.id == ausschuss_id
    ).first()
    if ausschuss:
        member_count = db.query(Mitgliedschaft).filter(
            Mitgliedschaft.ausschuss_id == ausschuss_id,
            Mitgliedschaft.periode_id == periode_id
        ).count()
        if member_count > 0:
            new_quorum = calculate_quorum(member_count)
            ausschuss.quorum_override = new_quorum
```

**Result:** Redirect to period detail page

---

#### 7. GET `/admin/perioden/{periode_id}/ausschuss-add`
**Handler:** `ausschuss_add_form()`
**Response:** HTML form

Form fields:
- `name` (String, required)
- `typ` (Select, required) - options from AusschussTyp enum
- `turnus` (String, optional)
- `aktiv` (Checkbox)

---

#### 8. POST `/admin/perioden/{periode_id}/ausschuss-add`
**Handler:** `ausschuss_add()`

**Validation:**
- name and typ are required
- typ must be valid AusschussTyp enum value

**Action:** Creates `Ausschuss` record:
```python
ausschuss = Ausschuss(
    periode_id=periode_id,
    name=name,
    typ=AusschussTyp(typ_str),
    turnus=turnus or None,
    aktiv=aktiv
)
```

**Result:** Redirect to period detail page

---

#### 9. GET `/admin/perioden/{periode_id}/edit`
**Handler:** `periode_edit()`
**Response:** HTML form

Pre-populated form with current values

---

#### 10. POST `/admin/perioden/{periode_id}/update`
**Handler:** `periode_update()`

**Fields Updated:**
- name
- start_jahr
- end_jahr
- aktiv

**Validation:**
- ValueError on invalid year format
- IntegrityError on duplicate name

**Result:** Redirect to periods list

---

#### 11. GET `/admin/perioden/{periode_id}/delete`
**Handler:** `periode_delete()`

**Pre-Delete Checks:**
```python
person_count = db.query(PeriodePerson).filter(
    PeriodePerson.periode_id == periode_id
).count()
ausschuss_count = db.query(Ausschuss).filter(
    Ausschuss.periode_id == periode_id
).count()

if person_count > 0 or ausschuss_count > 0:
    # Return error page with counts
    # User must remove all persons and committees first
else:
    db.delete(periode)
    db.commit()
```

**Result:** Redirect to periods list

---

## Templates

### `templates/perioden.html`
- Extends `base.html`
- Card-based layout for each period
- Status badges (Aktiv/Inaktiv)
- Statistics boxes (person count, committee count)
- Responsive two-column grid

Features:
- Color-coded status indicators
- Hover effects on period cards
- Quick action buttons
- Empty state message if no periods

### `templates/periode_detail.html`
- Extends `base.html`
- Two-column layout
- Left: Person management
- Right: Committee management
- Inline forms for adding items
- Quorum calculation info box

Features:
- Member tables with remove/edit actions
- Committee tables with member counts
- Type badges for committees
- Add forms with proper styling
- Back navigation

---

## Database Operations

### Model Relationships

```
Gemeinderatsperiode
├── PeriodePerson (1:n)
│   └── Person (n:1)
├── Ausschuss (1:n)
│   └── Mitgliedschaft (1:n)
│       └── Person (n:1)
└── Jahresplan (1:n)
```

### Key Queries

**Active persons in period:**
```python
db.query(PeriodePerson).filter(
    PeriodePerson.periode_id == periode_id,
    PeriodePerson.end_datum.is_(None)
).all()
```

**Committee members count:**
```python
db.query(Mitgliedschaft).filter(
    Mitgliedschaft.ausschuss_id == ausschuss_id,
    Mitgliedschaft.periode_id == periode_id
).count()
```

---

## Error Handling

All routes implement try/except with:
- ValueError: Invalid enum conversions, integer parsing
- IntegrityError: Unique constraint violations (duplicate names)
- Generic Exception: Unexpected errors

Error responses:
- Display user-friendly messages
- HTML error page with back button
- Database rollback on failure

---

## Security Features

1. **Authentication:** All routes check `is_logged_in()`
2. **XSS Prevention:** `escape_html()` on all user input display
3. **CSRF Protection:** Implicitly via HTTP POST/redirect pattern
4. **SQL Injection:** SQLAlchemy ORM prevents direct injection
5. **Input Validation:** Enum type checking, required field validation
6. **Redirect Validation:** `validate_redirect_url()` on all redirects

---

## Testing

All existing tests pass (11/11 ✓):
```
test_health ............................ PASSED
test_create_and_list_person ............ PASSED
test_set_verfuegbarkeit ................ PASSED
test_create_committee_with_members ..... PASSED
test_calculation_flow .................. PASSED
test_rules_get_and_update .............. PASSED
test_deactivate_activate_person ........ PASSED
test_transfer_agenda ................... PASSED
test_transfer_agenda_skips_duplicates .. PASSED
test_calculation_saves_results ......... PASSED
test_get_saved_results ................. PASSED
```

Quorum calculation test cases:
- 1 member  → quorum = 1
- 2 members → quorum = 1
- 3 members → quorum = 2
- 4 members → quorum = 2
- 5 members → quorum = 3
- 6 members → quorum = 3
- 7 members → quorum = 4
- 10 members → quorum = 5

---

## File Locations

- **Routes:** `C:\Projekte\ausschussplaner\app\api\routes\admin.py`
- **Templates:** `C:\Projekte\ausschussplaner\templates\`
  - `perioden.html`
  - `periode_detail.html`
- **Models:** `C:\Projekte\ausschussplaner\app\models\models.py` (no changes)

---

## Dashboard Integration

The main dashboard at `/admin` was updated:
- Added "Perioden" link to sidebar navigation
- Updated dashboard card to include "Perioden verwalten" link
- Period management now accessible from all admin pages via sidebar

---

## Usage Workflow

1. **Create Period:** Admin → Perioden → Neue Periode
   - Fill in name, start/end year
   - Activate by default

2. **Add Persons:** Admin → Perioden → [Period] → Add Person
   - Select from available persons
   - start_datum auto-filled to today
   - Creates PeriodePerson record

3. **Add Committees:** Admin → Perioden → [Period] → Add Committee
   - Enter name, select type, optional turnus
   - Associates with period

4. **Manage Memberships:** Admin → Ausschüsse → [Committee] → Members
   - Add/remove persons from committees
   - Assigns Rolle (Obmann, Obmann-Stellvertreter, Mitglied)

5. **Personnel Change:** Admin → Perioden → [Period] → Remove Person
   - Sets end_datum on PeriodePerson
   - Removes all memberships
   - Creates new Jahresplan variante with updated quorum

---

## Notes

- Quorum is calculated as `ceil(member_count / 2)` when members are removed
- Obmann presence is required separately (not calculated in quorum)
- Jahresplan variante increments when persons are removed from period
- All timestamps use `date.today()` for consistency
- Period names must be unique

---

## Future Enhancements

1. Batch import of persons from CSV
2. Audit trail for personnel changes
3. Email notifications on person removal
4. Period template cloning
5. Member role history tracking
