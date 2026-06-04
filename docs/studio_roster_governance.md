# Studio Roster Governance

Sprint 20: Multi-student studio support with local roster management.

## Purpose

The studio roster layer provides local organization for teachers and students. It enables a single teacher to manage multiple students, or multiple teachers to share a studio. The roster is local-first with no authentication, permissions, or cloud infrastructure.

## Data Model

### Studio

Top-level grouping for teachers and students:

```python
class Studio(BaseModel):
    studio_id: str  # studio_<12hex>
    name: str  # 1-200 chars
    teacher_ids: list[str]
    student_ids: list[str]
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
```

### Student

Lightweight student record:

```python
class Student(BaseModel):
    student_id: str  # student_<12hex>
    display_name: str  # 1-200 chars
    active: bool = True
    enrollment_date: datetime
    notes: Optional[str]  # max 1000 chars
    metadata: dict[str, Any]
```

### Teacher

Lightweight teacher record:

```python
class Teacher(BaseModel):
    teacher_id: str  # teacher_<12hex>
    display_name: str  # 1-200 chars
    active: bool = True
    metadata: dict[str, Any]
```

### StudioOverview

Aggregated roster state for display:

```python
class StudioOverview(BaseModel):
    studio_id: str
    name: str
    active_student_count: int
    active_teacher_count: int
    total_student_count: int
    total_teacher_count: int
    students: list[Student]
    teachers: list[Teacher]
    generated_at: datetime
```

## Event Log

Roster state is stored as an append-only event log:

```python
class StudioRosterEventType(str, Enum):
    studio_created = "studio_created"
    teacher_added = "teacher_added"
    student_added = "student_added"
    student_deactivated = "student_deactivated"
    teacher_deactivated = "teacher_deactivated"
    student_reactivated = "student_reactivated"
    teacher_reactivated = "teacher_reactivated"
    metadata_updated = "metadata_updated"

class StudioRosterEvent(BaseModel):
    id: Optional[str]  # sre_<12hex>, auto-generated
    event_type: StudioRosterEventType
    studio_id: str
    target_id: Optional[str]  # student_id or teacher_id
    payload: dict[str, Any]
    timestamp: datetime
    source: str = "studio_roster"
    version: str = "0.1"
```

## Governance Rules

1. **Soft delete only.** Students and teachers are deactivated, never removed. This preserves audit trail.

2. **No hard removal.** There is no event type for permanent deletion. All roster history is retained.

3. **IDs are stable.** Once assigned, `studio_id`, `student_id`, and `teacher_id` never change.

4. **One file may contain multiple studios.** The store supports multi-studio files for portability.

5. **Auto-resolve single studio.** If only one studio exists, methods accept `studio_id=None` and use that studio.

6. **Multiple studios require explicit ID.** With multiple studios, operations require explicit `studio_id` or raise `ValueError`.

7. **No authentication.** IDs are labels, not security principals. No permissions are enforced.

8. **Local-first only.** No cloud sync, multi-tenant infrastructure, or remote storage.

## Store Interface

```python
class StudioRosterStore:
    def __init__(self, path: Path) -> None: ...

    def create_studio(
        self,
        name: str,
        studio_id: str | None = None,
        teacher_ids: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Studio: ...

    def add_student(
        self,
        studio_id: str,
        display_name: str,
        student_id: str | None = None,
        enrollment_date: datetime | None = None,
        notes: str | None = None,
        metadata: dict | None = None,
    ) -> Student: ...

    def add_teacher(
        self,
        studio_id: str,
        display_name: str,
        teacher_id: str | None = None,
        metadata: dict | None = None,
    ) -> Teacher: ...

    def deactivate_student(self, studio_id: str, student_id: str) -> Student: ...
    def deactivate_teacher(self, studio_id: str, teacher_id: str) -> Teacher: ...
    def reactivate_student(self, studio_id: str, student_id: str) -> Student: ...
    def reactivate_teacher(self, studio_id: str, teacher_id: str) -> Teacher: ...

    def get_studio(self, studio_id: str | None = None) -> Studio | None: ...
    def list_students(self, studio_id: str | None = None, active_only: bool = True) -> list[Student]: ...
    def list_teachers(self, studio_id: str | None = None, active_only: bool = True) -> list[Teacher]: ...
    def build_overview(self, studio_id: str | None = None) -> StudioOverview: ...
```

## CLI Usage

```bash
# Create a studio
sg-coach studio create --roster roster.jsonl --name "Downtown Music Studio"

# Add students
sg-coach studio add-student --roster roster.jsonl --name "Alice"
sg-coach studio add-student --roster roster.jsonl --name "Bob" --notes "Beginner"

# Add teachers
sg-coach studio add-teacher --roster roster.jsonl --name "Mr. Smith"

# List members
sg-coach studio list-students --roster roster.jsonl
sg-coach studio list-teachers --roster roster.jsonl
sg-coach studio list-students --roster roster.jsonl --all  # Include inactive

# View overview
sg-coach studio overview --roster roster.jsonl --pretty

# Multiple studios
sg-coach studio create --roster roster.jsonl --name "Studio A" --studio-id studio_a
sg-coach studio create --roster roster.jsonl --name "Studio B" --studio-id studio_b
sg-coach studio add-student --roster roster.jsonl --studio-id studio_a --name "Carol"
```

## ID Prefixes

| Entity | Prefix | Example |
|--------|--------|---------|
| Studio | `studio_` | `studio_abc123def456` |
| Student | `student_` | `student_abc123def456` |
| Teacher | `teacher_` | `teacher_abc123def456` |
| Event | `sre_` | `sre_abc123def456` |

All IDs use 12 hex characters (6 bytes from `secrets.token_hex(6)`).

## Limitations

- No authentication or permissions
- No cloud sync
- No student-facing views
- No multi-tenant infrastructure
- No cross-student analytics (deferred)
- No curriculum authoring

## Definition of Done

Sprint 20 is complete when:
- Studio/Student/Teacher/StudioOverview schemas exist
- StudioRosterEventType enum covers all event types
- StudioRosterStore persists to JSONL
- Event log rebuilds current state correctly
- CLI commands work: create, add-student, add-teacher, list-students, list-teachers, overview
- Auto-resolve works for single studio
- Multiple studios require explicit ID
- Deactivation/reactivation works
- All tests pass
- No auth/permissions added
- No cloud infrastructure added
