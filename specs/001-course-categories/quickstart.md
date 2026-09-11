# Quickstart Validation Guide: Course Categories Management

**Feature**: `001-course-categories`  
**Date**: 2026-09-11  
**Spec Reference**: [spec.md](file:///Users/anilvattam/.gemini/antigravity-ide/scratch/lms-platform/specs/001-course-categories/spec.md)

## Overview

This guide details the end-to-end verification workflows for validating the Course Categories feature across both backend APIs and the frontend `AdminCategories.jsx` user interface.

## Prerequisites

1. Backend running locally on `http://localhost:8000` (or inside Docker).
2. Frontend running locally on `http://localhost:5173` (or Netlify preview).
3. Logged-in administrative user account.

---

## Scenario 1: Create a New Course Category

### Steps
1. Navigate to `/admin/categories` or click **🏷️ Categories** from the Admin navigation bar.
2. In the left Master panel, click **+ Add Category**.
3. Enter Category Name: `Full-Stack Web Development`, Description: `Modern frontend and backend engineering.`, and pick an icon/color.
4. Click **Create Category**.

### Expected Outcome
- The new category is created via `POST /api/admin/categories`.
- It appears immediately in the left panel list with a `0 Courses` badge.
- Success toast notification is displayed.

---

## Scenario 2: Assign Courses to Category

### Steps
1. Select `Full-Stack Web Development` from the left panel.
2. In the right Detail panel, view the **Assigned Courses** section.
3. In the course search/picker, select 2 available courses (e.g., "React Essentials" and "FastAPI Fundamentals").
4. Click **Save Assignments**.

### Expected Outcome
- Courses are assigned via `POST /api/admin/categories/{category_id}/courses`.
- The right panel shows the 2 assigned courses with options to unlink them.
- The left panel badge updates to `2 Courses`.

---

## Scenario 3: Update Category Details

### Steps
1. With `Full-Stack Web Development` selected, click **Edit Category** (or update inline fields).
2. Change the name to `Full-Stack & Cloud Engineering`.
3. Click **Save Changes**.

### Expected Outcome
- Updated via `PUT /api/admin/categories/{category_id}`.
- Updated name and slug reflect immediately on both left and right panels.

---

## Scenario 4: Non-Destructive Category Deletion

### Steps
1. With `Full-Stack & Cloud Engineering` selected (which has 2 courses assigned), click **Delete Category**.
2. Confirm the deletion in the modal dialog.

### Expected Outcome
- `DELETE /api/admin/categories/{category_id}` succeeds.
- Category is removed from the left panel.
- Right panel resets to the empty/selection state.
- **Verification**: Navigating to `/admin/courses` confirms that both courses still exist with 0 data loss or corruption.
