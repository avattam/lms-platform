# Phase 0 Research: Course Categories Management

**Feature**: `001-course-categories`  
**Date**: 2026-09-11  
**Spec Reference**: [spec.md](file:///Users/anilvattam/.gemini/antigravity-ide/scratch/lms-platform/specs/001-course-categories/spec.md)

## Architectural & Technical Decisions

### Decision 1: Database Model & Many-to-Many Relationship Architecture
- **Decision**: Create a `CourseCategory` model and a `course_category_associations` junction table in `backend/models/db_models.py` using SQLAlchemy 2.0 Async mapped columns.
- **Rationale**:
  - The feature clarification established an N:M relationship where courses can belong to multiple categories simultaneously.
  - Foreign key constraints with `ondelete="CASCADE"` on the junction table ensure that deleting a category cleanly removes the association rows without touching or modifying the `Course` records or student progress.
  - Case-insensitive uniqueness on `CourseCategory.name` prevents duplicate taxonomies.
- **Alternatives Considered**:
  - *Single Foreign Key on Course*: Rejected per clarification Q1 (courses need multi-category associations).
  - *PostgreSQL Array Column of strings*: Rejected because it lacks relational referential integrity, foreign key cascading, and efficient joins for course counts.

---

### Decision 2: Backend API Structure & Dedicated Router
- **Decision**: Create a dedicated router in `backend/routers/admin_categories.py` for admin operations (`/admin/categories/*`) and public read operations (`/categories`), mounted in `backend/main.py`.
- **Rationale**:
  - Keeps the routing modular and decoupled from `admin_courses.py` and `courses.py`.
  - Follows the existing pattern seen in `admin_users.py` and `admin_courses.py`.
  - Enforces role-based access control via `require_admin` dependency for mutating endpoints.
- **Endpoints**:
  - `POST /admin/categories`: Create category (name, description, color/icon).
  - `GET /admin/categories`: List all categories with assigned course counts.
  - `GET /admin/categories/{category_id}`: Get single category with list of assigned courses.
  - `PUT /admin/categories/{category_id}`: Update category details.
  - `DELETE /admin/categories/{category_id}`: Delete category (cascades junction rows, leaves courses intact).
  - `POST /admin/categories/{category_id}/courses`: Batch assign/sync courses to category.
  - `DELETE /admin/categories/{category_id}/courses/{course_id}`: Remove specific course from category.
  - `GET /categories`: Public endpoint for active course catalog browsing.

---

### Decision 3: Frontend Architecture & Master-Detail UX
- **Decision**: Create `frontend/src/pages/AdminCategories.jsx` implementing a responsive Two-Panel Master-Detail layout.
- **Rationale**:
  - Left panel: Searchable list of categories with course count badges, "+ New Category" button, edit/delete actions.
  - Right panel: Detail view of the selected category, category edit form, list of currently assigned courses, and a searchable multi-select course picker to toggle course associations.
  - Follows the platform's Design System (`design.md`) with Luminous Slate & Indigo theme tokens, learning-centric iconography (`🏷️`, `📚`, `➕`, `🗑️`, `✏️`), and 300ms smooth CSS transitions.

---

### Decision 4: Integration with Navigation & Routing
- **Decision**:
  - Add `/admin/categories` protected route to `frontend/src/App.jsx` with `adminOnly={true}`.
  - Add `🏷️ Categories` navigation link across all admin pages (`Dashboard.jsx`, `AdminCourses.jsx`, `AdminUsers.jsx`, `AdminCategories.jsx`).
- **Rationale**:
  - Ensures seamless administrative navigation between Users, Curriculum Courses, and Course Categories.
