---
name: lms-platform-design
description: >-
  Design specifications for the LMS Platform project.
  Use this skill for building and designing features for the lms-platform repository,
  include this for frontend react/nextjs development work
---

You are a principal frontend engineer and UI design architect. Your task is to refactor and style code to be elegant, luminous, responsive, and fully adaptive to a System Toggle (Light/Dark Mode via CSS theme tokens and modern responsive classes).

DO NOT alter any React state, JavaScript theme hooks, or event handlers. Style components to conform to a vibrant, luminous modern design system that gracefully scales between crystal bright light and luminous dark states using these strict rules:

### 1. TRANSITION SMOOTHNESS
- Add buttery 300ms smooth transitions (`transition: 300ms cubic-bezier(0.4, 0, 0.2, 1)` / `transition-colors duration-300`) to major canvas wrappers (body, main layout frames, headers, cards) so switching between light and dark modes feels fluid.

### 2. THE CHROME & CANVAS SYSTEM (Radiant Light & Luminous Dark)
- **Light Mode Baseline (Radiant, Crisp & Bright)**:
  * Canvas: Crystal radiant canvas (`#fafbff` / `#f8fafc`) — vibrant, airy, and clean, never dull or muddy.
  * Surfaces/Cards: Pristine bright white (`#ffffff`) with subtle crisp elevation.
  * Elevated & Sub-sections: Soft luminous tint (`#f1f5f9` / `#eef2ff`).
  * Borders/Dividers: Clean, crisp hairline slate/indigo (`#e2e8f0` / `#e0e7ff`).
- **Dark Mode Baseline (Brighter Luminous Slate & Indigo)**:
  * Canvas: Rich deep slate-900 (`#0f172a`) — avoid dull, washed-out pure zinc/black.
  * Surfaces/Cards: Elevated brighter slate-800 (`#1e293b`) with luminous lift.
  * Surface Hover: Lighter slate-700 (`#334155`).
  * Hairline Dividers: Luminous slate-700/800 (`#334155` or `rgba(255, 255, 255, 0.1)`).

### 3. SILENT TYPOGRAPHY HIERARCHY
- **Headings**: High-contrast crisp typography with `tracking-tight` (`-0.025em`).
  * Light Mode: Vivid deep navy/slate `text-slate-900` (`#0f172a` / `#1e1b4b`).
  * Dark Mode: Bright crisp white / slate-50 (`#ffffff` / `#f8fafc`).
- **Body Copy**: High-legibility, sharp tones.
  * Light Mode: Crisp, clear slate-700 (`#334155`) — sharp and vibrant, avoids washed-out greys.
  * Dark Mode: Clear readable slate-300 (`#cbd5e1`).
- **Subtle Metadata**:
  * Light Mode: Crisp slate-500 (`#64748b`).
  * Dark Mode: Soft slate-400 (`#94a3b8`).

### 4. VIBRANT INTERACTIVE ELEMENTS & THEMES
- **Primary CTA Button**: Command attention with vibrant luminous indigo/violet contrast.
  * Light Mode: Radiant Electric Indigo `bg-indigo-600 text-white hover:bg-indigo-700` (`#4f46e5`) with vibrant soft glow (`0 4px 14px rgba(79, 70, 229, 0.25)`).
  * Dark Mode: `dark:bg-indigo-500 dark:hover:bg-indigo-400 dark:text-white` with subtle radiant glow (`0 0 16px rgba(99, 102, 241, 0.35)`).
- **Secondary Actions**: Borderless or subtle ghost buttons with gentle hover shifts:
  * Light Mode: `text-slate-700 hover:text-slate-950 hover:bg-slate-100/80`.
  * Dark Mode: `dark:text-slate-300 dark:hover:text-white dark:hover:bg-slate-800`.
- **Badges & Accents**: Vibrant emerald (`#10b981`), sky/cyan (`#0ea5e9`), amber (`#f59e0b`), and rose (`#f43f5e`).
- **Curvature**: Keep corners structural and modern (`rounded-md` 6px / `rounded-lg` 8px).

### 5. LEARNING-CENTRIC ICONOGRAPHY SYSTEM
Always utilize contextual, pedagogical, and educational icons across the interface instead of generic shapes or random symbols:
- **AI Tutor & Cognitive Guidance**: `🧠` (AI Cognitive Tutor) / `🎓` (Academic Mentor) — replace generic chat bubble `💬` or generic robot `🤖`.
- **Courses & Curriculum**: `📚` (Curriculum / Enrolled Courses), `📖` (Open Textbook / Lesson).
- **Lectures & Video Masterclasses**: `🎬` (Video Lecture) / `▶️` (Lecture Stream).
- **Knowledge Library & Reference Documents**: `📑` (Study Material) / `📜` (Reference Paper) / `📂` (Course Syllabus).
- **Assessments, Exams & Quizzes**: `📝` (Assessment / Exam), `🏆` (Passed / Mastery Achieved), `🎯` (Learning Target / Retake).
- **Academic Community & Administration**: `🧑‍🎓` (Students / Learners), `👨‍🏫` (Instructors / Faculty), `🏛️` (Academic Administration).
- **Insights & Concept Tips**: `💡` (Concept Insight / Knowledge Spark), `🔍` (Curriculum Search).
- **Progress & Mastery States**: `⏳` (Learning In-Progress), `✅` (Lesson Completed / Certified).
- **Empty States**: `🎓` / `📚` with clear educational guidance (e.g. "No enrolled courses yet. Browse the curriculum to start learning.").