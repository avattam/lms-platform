# Tasks: Course Categories Management

**Feature**: `001-course-categories`  
**Plan**: [plan.md](file:///Users/anilvattam/.gemini/antigravity-ide/scratch/lms-platform/specs/001-course-categories/plan.md)  
**Spec**: [spec.md](file:///Users/anilvattam/.gemini/antigravity-ide/scratch/lms-platform/specs/001-course-categories/spec.md)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify and prepare project structure for the categories feature

- [X] T001 Verify database migration environment and create category model schema definitions in backend/models/db_models.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend database models and Pydantic schemas required by all user stories

**⚠️ CRITICAL**: Must complete before user story implementation

- [X] T002 Implement `CourseCategory` and `CourseCategoryAssociation` models with foreign keys, cascading delete on junction table, and case-insensitive unique constraint in backend/models/db_models.py
- [X] T003 [P] Implement Pydantic request and response schemas (`CategoryIn`, `CategoryOut`, `CategoryUpdate`, `CategoryWithCoursesOut`, `CategoryCourseSync`) in backend/schemas/pydantic_schemas.py
- [X] T004 Create base API router skeleton `admin_categories.py` in backend/routers/admin_categories.py and mount in backend/main.py

**Checkpoint**: Foundation ready — database entities and schema validation available for all category workflows

---

## Phase 3: User Story 1 - Create and Manage Course Categories (Priority: P1) 🎯 MVP

**Goal**: Enable administrators to create, view, edit, and delete course categories with real-time feedback

**Independent Test**: Create a category via API/UI, update its name and description, view the category list with course count badges, and delete an unused category.

### Implementation for User Story 1

- [X] T005 [US1] Implement Category CRUD endpoints (`GET /admin/categories`, `POST /admin/categories`, `PUT /admin/categories/{category_id}`, `DELETE /admin/categories/{category_id}`, `GET /categories`) in backend/routers/admin_categories.py
- [X] T006 [US1] Implement duplicate name validation and slug generation logic in backend/routers/admin_categories.py
- [X] T007 [US1] Create `AdminCategories.jsx` with Master panel listing all categories, search bar, and "+ Add Category" modal in frontend/src/pages/AdminCategories.jsx
- [X] T008 [US1] Implement category edit modal and inline updates in frontend/src/pages/AdminCategories.jsx

**Checkpoint**: User Story 1 is functional — Admins can perform full Category CRUD with instant UI feedback.

---

## Phase 4: User Story 2 - Assign and Reassign Courses to Categories (Priority: P2)

**Goal**: Enable administrators to assign and manage course associations for any selected category using the master-detail layout

**Independent Test**: Select a category on the left panel, view assigned courses on the right panel, search available courses and assign/unassign them, verifying badge counters update immediately.

### Implementation for User Story 2

- [X] T009 [US2] Implement `GET /admin/categories/{category_id}` and course assignment endpoints (`POST /admin/categories/{category_id}/courses`, `DELETE /admin/categories/{category_id}/courses/{course_id}`) in backend/routers/admin_categories.py
- [X] T010 [US2] Build Detail panel in `AdminCategories.jsx` displaying selected category metadata, assigned courses list, and active course counters in frontend/src/pages/AdminCategories.jsx
- [X] T011 [US2] Build searchable multi-select Course Assignment Picker in Detail panel allowing admins to search courses and toggle category associations in frontend/src/pages/AdminCategories.jsx
- [X] T012 [US2] Add quick-remove action for unlinking individual courses directly from the assigned courses list in frontend/src/pages/AdminCategories.jsx

**Checkpoint**: User Stories 1 AND 2 are functional — Admins can manage categories and flexibly assign/reassign courses.

---

## Phase 5: User Story 3 - Safe Category Deletion and Course Protection (Priority: P3)

**Goal**: Ensure category deletion safely unlinks category associations without deleting or corrupting assigned courses

**Independent Test**: Assign courses to a category, delete the category, and confirm courses remain intact in the system.

### Implementation for User Story 3

- [X] T013 [US3] Add deletion confirmation modal with clear safety warning explaining that assigned courses will become uncategorized in frontend/src/pages/AdminCategories.jsx
- [X] T014 [US3] Verify backend `DELETE /admin/categories/{category_id}` cleanly removes association rows from `course_category_associations` while leaving `Course` records unchanged in backend/routers/admin_categories.py

**Checkpoint**: All user stories functional with data integrity guarantees.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Navigation integration, styling alignment, and end-to-end quickstart validation

- [X] T015 [P] Register `/admin/categories` protected admin route in frontend/src/App.jsx
- [X] T016 [P] Add `🏷️ Categories` navigation link to admin navbars in frontend/src/pages/Dashboard.jsx, frontend/src/pages/AdminCourses.jsx, frontend/src/pages/AdminUsers.jsx, and frontend/src/pages/AdminCategories.jsx
- [X] T017 Verify responsive layout, Luminous Slate & Indigo theme tokens, and educational iconography per design.md in frontend/src/pages/AdminCategories.jsx
- [X] T018 Execute full quickstart validation scenarios from specs/001-course-categories/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 (Foundational)
- **User Story 2 (Phase 4)**: Depends on Phase 2 & Phase 3 (extends `AdminCategories.jsx` master panel with detail assignment panel)
- **User Story 3 (Phase 5)**: Depends on Phase 3 & Phase 4
- **Polish (Phase 6)**: Depends on User Story phases 3-5

### Parallel Opportunities

- `T003` (Pydantic schemas) can be written in parallel with `T002` (SQLAlchemy models).
- `T015` and `T016` (App route and navbar links) can be updated in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 & Phase 2 (Foundational models & schemas).
2. Complete Phase 3 (Category CRUD backend endpoints + Master panel UI in `AdminCategories.jsx`).
3. Validate independent category creation, listing, updating, and deletion.

### Incremental Delivery
1. Foundation (Models + Schemas + Router)
2. MVP: Category CRUD (US1)
3. Multi-course Assignment & Master-Detail UX (US2)
4. Safe Deletion & Data Protection Confirmation (US3)
5. Navigation integration & Quickstart validation (Polish)
