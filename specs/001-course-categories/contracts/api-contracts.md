# Interface Contracts: Course Categories Management

**Feature**: `001-course-categories`  
**Date**: 2026-09-11  
**Spec Reference**: [spec.md](file:///Users/anilvattam/.gemini/antigravity-ide/scratch/lms-platform/specs/001-course-categories/spec.md)

## REST API Endpoints

### 1. List Categories (Admin)
- **Endpoint**: `GET /api/admin/categories`
- **Auth**: Required (`role: admin`)
- **Response**: `200 OK`
```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Web Development",
    "slug": "web-development",
    "description": "Full-stack web engineering with modern frameworks",
    "icon": "🌐",
    "color": "#6366f1",
    "course_count": 5,
    "created_at": "2026-09-11T12:00:00Z",
    "updated_at": "2026-09-11T12:00:00Z"
  }
]
```

---

### 2. Create Category (Admin)
- **Endpoint**: `POST /api/admin/categories`
- **Auth**: Required (`role: admin`)
- **Request Body**:
```json
{
  "name": "Machine Learning & AI",
  "description": "Foundations of neural networks and LLMs",
  "icon": "🧠",
  "color": "#8b5cf6"
}
```
- **Response**: `201 Created`
```json
{
  "id": "7ca85f64-5717-4562-b3fc-2c963f66afa7",
  "name": "Machine Learning & AI",
  "slug": "machine-learning-ai",
  "description": "Foundations of neural networks and LLMs",
  "icon": "🧠",
  "color": "#8b5cf6",
  "course_count": 0,
  "created_at": "2026-09-11T12:05:00Z",
  "updated_at": "2026-09-11T12:05:00Z"
}
```
- **Error Responses**:
  - `400 Bad Request`: Empty name
  - `409 Conflict`: Category with this name already exists

---

### 3. Get Category with Courses (Admin)
- **Endpoint**: `GET /api/admin/categories/{category_id}`
- **Auth**: Required (`role: admin`)
- **Response**: `200 OK`
```json
{
  "id": "7ca85f64-5717-4562-b3fc-2c963f66afa7",
  "name": "Machine Learning & AI",
  "slug": "machine-learning-ai",
  "description": "Foundations of neural networks and LLMs",
  "icon": "🧠",
  "color": "#8b5cf6",
  "course_count": 2,
  "courses": [
    {
      "id": "a1a85f64-5717-4562-b3fc-2c963f66af11",
      "title": "Introduction to Deep Learning",
      "description": "Core concepts of neural networks",
      "is_published": true,
      "assigned_at": "2026-09-11T12:10:00Z"
    }
  ]
}
```

---

### 4. Update Category (Admin)
- **Endpoint**: `PUT /api/admin/categories/{category_id}`
- **Auth**: Required (`role: admin`)
- **Request Body**:
```json
{
  "name": "AI & Deep Learning",
  "description": "Advanced neural networks, generative AI, and RAG",
  "icon": "🤖",
  "color": "#ec4899"
}
```
- **Response**: `200 OK`

---

### 5. Delete Category (Admin)
- **Endpoint**: `DELETE /api/admin/categories/{category_id}`
- **Auth**: Required (`role: admin`)
- **Response**: `200 OK`
```json
{
  "message": "Category deleted successfully."
}
```

---

### 6. Batch Sync / Assign Courses to Category (Admin)
- **Endpoint**: `POST /api/admin/categories/{category_id}/courses`
- **Auth**: Required (`role: admin`)
- **Request Body**:
```json
{
  "course_ids": [
    "a1a85f64-5717-4562-b3fc-2c963f66af11",
    "b2b85f64-5717-4562-b3fc-2c963f66af22"
  ]
}
```
- **Response**: `200 OK`
```json
{
  "message": "Course assignments updated successfully.",
  "assigned_count": 2
}
```

---

### 7. Remove Course from Category (Admin)
- **Endpoint**: `DELETE /api/admin/categories/{category_id}/courses/{course_id}`
- **Auth**: Required (`role: admin`)
- **Response**: `200 OK`
```json
{
  "message": "Course removed from category."
}
```

---

### 8. List Categories for Public / Student Browse
- **Endpoint**: `GET /api/categories`
- **Auth**: Optional / Authenticated user
- **Response**: `200 OK` (list of categories with active course counts)
