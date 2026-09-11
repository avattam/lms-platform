import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

const ICON_PRESETS = ['🏷️', '🌐', '🧠', '💻', '📱', '📊', '🎨', '🛡️', '⚙️', '🚀', '📚', '🔬', '📐', '🤖', '💡'];
const COLOR_PRESETS = [
  { name: 'Indigo', hex: '#6366f1' },
  { name: 'Sky', hex: '#0284c7' },
  { name: 'Emerald', hex: '#10b981' },
  { name: 'Rose', hex: '#f43f5e' },
  { name: 'Amber', hex: '#f59e0b' },
  { name: 'Violet', hex: '#8b5cf6' },
  { name: 'Pink', hex: '#ec4899' },
  { name: 'Slate', hex: '#64748b' },
];

export default function AdminCategories() {
  const [categories, setCategories] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [categoryDetail, setCategoryDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [courseSearch, setCourseSearch] = useState('');

  // Course assignment state for the selected category
  const [selectedCourseIds, setSelectedCourseIds] = useState(new Set());
  const [savingAssignments, setSavingAssignments] = useState(false);

  // Modal States
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' | 'edit'
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    icon: '🏷️',
    color: '#6366f1',
  });
  const [formError, setFormError] = useState('');
  const [formSubmitting, setFormSubmitting] = useState(false);

  // Delete Confirmation Modal State
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [categoryToDelete, setCategoryToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Toast / Status notification
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    fetchInitialData();
  }, []);

  function showToast(msg, type = 'success') {
    setNotification({ msg, type });
    setTimeout(() => {
      setNotification(null);
    }, 4000);
  }

  async function fetchInitialData() {
    setLoading(true);
    try {
      const [catsRes, coursesRes] = await Promise.all([
        api.get('/admin/categories'),
        api.get('/admin/courses'),
      ]);
      setCategories(catsRes.data);
      setAllCourses(coursesRes.data);
      if (catsRes.data.length > 0 && !selectedCategory) {
        openCategory(catsRes.data[0]);
      }
    } catch (err) {
      console.error('Failed to fetch categories or courses:', err);
      showToast(err.response?.data?.detail || 'Failed to load category data', 'danger');
    } finally {
      setLoading(false);
    }
  }

  async function openCategory(category) {
    setSelectedCategory(category);
    setDetailLoading(true);
    setCourseSearch('');
    try {
      const { data } = await api.get(`/admin/categories/${category.id}`);
      setCategoryDetail(data);
      setSelectedCourseIds(new Set((data.courses || []).map(c => c.id)));
    } catch (err) {
      console.error('Failed to fetch category detail:', err);
      showToast('Failed to load category courses.', 'danger');
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshCategories(keepSelectedId = null) {
    try {
      const { data } = await api.get('/admin/categories');
      setCategories(data);
      if (keepSelectedId) {
        const found = data.find(c => c.id === keepSelectedId);
        if (found) {
          setSelectedCategory(found);
          const detailRes = await api.get(`/admin/categories/${found.id}`);
          setCategoryDetail(detailRes.data);
          setSelectedCourseIds(new Set((detailRes.data.courses || []).map(c => c.id)));
        }
      }
    } catch (err) {
      console.error('Failed to refresh categories:', err);
    }
  }

  // --- Category Create / Edit Form ---
  function openCreateModal() {
    setFormData({
      name: '',
      description: '',
      icon: '🏷️',
      color: '#6366f1',
    });
    setFormError('');
    setModalMode('create');
    setModalOpen(true);
  }

  function openEditModal(category, e) {
    if (e) e.stopPropagation();
    setFormData({
      name: category.name,
      description: category.description || '',
      icon: category.icon || '🏷️',
      color: category.color || '#6366f1',
    });
    setFormError('');
    setModalMode('edit');
    setModalOpen(true);
  }

  async function handleCategorySubmit(e) {
    e.preventDefault();
    if (!formData.name.trim()) {
      setFormError('Category name is required.');
      return;
    }
    setFormError('');
    setFormSubmitting(true);

    try {
      if (modalMode === 'create') {
        const { data } = await api.post('/admin/categories', formData);
        showToast(`Category "${data.name}" created successfully!`);
        setModalOpen(false);
        await refreshCategories(data.id);
      } else {
        const targetId = selectedCategory?.id;
        const { data } = await api.put(`/admin/categories/${targetId}`, formData);
        showToast(`Category "${data.name}" updated successfully!`);
        setModalOpen(false);
        await refreshCategories(data.id);
      }
    } catch (err) {
      setFormError(err.response?.data?.detail || 'An error occurred while saving category.');
    } finally {
      setFormSubmitting(false);
    }
  }

  // --- Category Deletion ---
  function promptDeleteCategory(category, e) {
    if (e) e.stopPropagation();
    setCategoryToDelete(category);
    setDeleteModalOpen(true);
  }

  async function confirmDeleteCategory() {
    if (!categoryToDelete) return;
    setDeleting(true);
    try {
      await api.delete(`/admin/categories/${categoryToDelete.id}`);
      showToast(`Category "${categoryToDelete.name}" deleted. Courses were safely preserved.`);
      setDeleteModalOpen(false);
      setCategoryToDelete(null);
      if (selectedCategory?.id === categoryToDelete.id) {
        setSelectedCategory(null);
        setCategoryDetail(null);
      }
      await refreshCategories();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete category.');
    } finally {
      setDeleting(false);
    }
  }

  // --- Course Assignment / Unlink ---
  function toggleCourseSelection(courseId) {
    setSelectedCourseIds(prev => {
      const next = new Set(prev);
      if (next.has(courseId)) {
        next.delete(courseId);
      } else {
        next.add(courseId);
      }
      return next;
    });
  }

  async function saveCourseAssignments() {
    if (!selectedCategory) return;
    setSavingAssignments(true);
    try {
      const payload = { course_ids: Array.from(selectedCourseIds) };
      await api.post(`/admin/categories/${selectedCategory.id}/courses`, payload);
      showToast('Course assignments synchronized successfully!');
      await refreshCategories(selectedCategory.id);
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to save course assignments.', 'danger');
    } finally {
      setSavingAssignments(false);
    }
  }

  async function removeSingleCourse(courseId, courseTitle, e) {
    if (e) e.stopPropagation();
    if (!selectedCategory) return;
    try {
      await api.delete(`/admin/categories/${selectedCategory.id}/courses/${courseId}`);
      showToast(`Unlinked "${courseTitle}" from category.`);
      await refreshCategories(selectedCategory.id);
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to unlink course.', 'danger');
    }
  }

  // Filtered categories
  const filteredCategories = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return categories;
    return categories.filter(
      c =>
        c.name.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q)) ||
        (c.slug && c.slug.toLowerCase().includes(q))
    );
  }, [categories, search]);

  // Filtered courses for assignment picker
  const filteredCourses = useMemo(() => {
    const q = courseSearch.trim().toLowerCase();
    if (!q) return allCourses;
    return allCourses.filter(
      c =>
        c.title.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q))
    );
  }, [allCourses, courseSearch]);

  const assignedCount = categoryDetail?.courses?.length || 0;

  return (
    <div className="admin-layout">
      {/* Admin Navigation Bar */}
      <div className="admin-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h1>Course Categories 🏷️</h1>
          <span className="badge badge-admin">{categories.length} Categories</span>
        </div>
        <div className="tab-bar">
          <Link to="/admin/users" className="tab">🧑‍🎓 Users</Link>
          <Link to="/admin/courses" className="tab">📚 Curriculum</Link>
          <Link to="/admin/categories" className="tab active">🏷️ Categories</Link>
        </div>
        <Link to="/dashboard" className="btn-ghost">← Dashboard</Link>
      </div>

      {/* Floating Toast Notification */}
      {notification && (
        <div
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 2000,
            padding: '0.85rem 1.25rem',
            background: notification.type === 'danger' ? 'var(--danger)' : 'var(--primary)',
            color: '#fff',
            borderRadius: 'var(--radius)',
            boxShadow: 'var(--shadow-lg)',
            fontWeight: 500,
            fontSize: '0.9rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            animation: 'fadeIn 0.2s ease-out',
          }}
        >
          <span>{notification.type === 'danger' ? '⚠️' : '✅'}</span>
          <span>{notification.msg}</span>
        </div>
      )}

      {/* Main Content: Master-Detail Layout */}
      <div className="admin-content" style={{ display: 'flex', width: '100%', minHeight: 'calc(100vh - 75px)' }}>
        {/* ================= Master Panel (Left) ================= */}
        <div
          className="course-manager"
          style={{
            flex: '0 0 440px',
            maxWidth: '460px',
            borderRight: '1px solid var(--border)',
            padding: '1.5rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          <div className="manager-header" style={{ marginBottom: 0 }}>
            <div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>All Categories</h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                Organize curriculum into targeted topics
              </p>
            </div>
            <button className="btn-primary btn-sm" onClick={openCreateModal}>
              + Add Category
            </button>
          </div>

          {/* Search bar */}
          <div style={{ position: 'relative' }}>
            <input
              className="form-input"
              style={{ width: '100%', paddingLeft: '2rem' }}
              placeholder="Filter categories by name or topic…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <span
              style={{
                position: 'absolute',
                left: '0.65rem',
                top: '50%',
                transform: 'translateY(-50%)',
                fontSize: '0.85rem',
                opacity: 0.6,
              }}
            >
              🔍
            </span>
            {search && (
              <button
                className="btn-ghost"
                style={{
                  position: 'absolute',
                  right: '0.4rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  padding: '0.2rem 0.4rem',
                  fontSize: '0.75rem',
                }}
                onClick={() => setSearch('')}
              >
                ✕
              </button>
            )}
          </div>

          {/* Category List */}
          <div className="course-list" style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <p className="empty-text" style={{ textAlign: 'center', padding: '2rem' }}>
                Loading categories…
              </p>
            ) : filteredCategories.length === 0 ? (
              <div
                style={{
                  textAlign: 'center',
                  padding: '2.5rem 1rem',
                  background: 'var(--surface)',
                  borderRadius: 'var(--radius)',
                  border: '1px dashed var(--border)',
                }}
              >
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.5rem' }}>🏷️</span>
                <p style={{ fontWeight: 600, color: 'var(--text)' }}>No categories found</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '1rem' }}>
                  {search ? 'Try adjusting your search query.' : 'Get started by creating your first category.'}
                </p>
                {!search && (
                  <button className="btn-primary btn-sm" onClick={openCreateModal}>
                    + Create Category
                  </button>
                )}
              </div>
            ) : (
              filteredCategories.map(cat => {
                const isSelected = selectedCategory?.id === cat.id;
                return (
                  <div
                    key={cat.id}
                    className={`course-row ${isSelected ? 'selected' : ''}`}
                    onClick={() => openCategory(cat)}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'stretch',
                      gap: '0.5rem',
                      padding: '0.85rem 1rem',
                      borderLeft: `4px solid ${cat.color || 'var(--primary)'}`,
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                        <div
                          style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: 'var(--radius-sm)',
                            background: `${cat.color || '#6366f1'}22`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.15rem',
                          }}
                        >
                          {cat.icon || '🏷️'}
                        </div>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text)' }}>
                            {cat.name}
                          </div>
                          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'ui-monospace, monospace' }}>
                            /{cat.slug}
                          </div>
                        </div>
                      </div>

                      <span
                        className="badge"
                        style={{
                          background: cat.course_count > 0 ? 'var(--primary-hover)' : 'var(--bg-3)',
                          color: '#fff',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                        }}
                      >
                        {cat.course_count} {cat.course_count === 1 ? 'Course' : 'Courses'}
                      </span>
                    </div>

                    {cat.description && (
                      <p
                        style={{
                          fontSize: '0.8rem',
                          color: 'var(--text-muted)',
                          lineHeight: 1.4,
                          margin: 0,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                        }}
                      >
                        {cat.description}
                      </p>
                    )}

                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'flex-end',
                        gap: '0.4rem',
                        marginTop: '0.25rem',
                      }}
                      onClick={e => e.stopPropagation()}
                    >
                      <button
                        className="btn-sm"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={e => openEditModal(cat, e)}
                        title="Edit category details"
                      >
                        ✏️ Edit
                      </button>
                      <button
                        className="btn-sm btn-danger"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={e => promptDeleteCategory(cat, e)}
                        title="Delete category"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ================= Detail Panel (Right) ================= */}
        <div
          className="detail-panel"
          style={{
            flex: 1,
            padding: '1.75rem 2rem',
            overflowY: 'auto',
            background: 'var(--bg)',
          }}
        >
          {selectedCategory ? (
            <div style={{ maxWidth: '900px', display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
              {/* Category Header Card */}
              <div
                style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  padding: '1.5rem',
                  boxShadow: 'var(--shadow)',
                  position: 'relative',
                  borderTop: `4px solid ${selectedCategory.color || 'var(--primary)'}`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <div
                      style={{
                        width: '54px',
                        height: '54px',
                        borderRadius: 'var(--radius)',
                        background: `${selectedCategory.color || '#6366f1'}25`,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '2rem',
                        border: `1px solid ${selectedCategory.color || '#6366f1'}44`,
                      }}
                    >
                      {selectedCategory.icon || '🏷️'}
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                        <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>{selectedCategory.name}</h2>
                        <span
                          style={{
                            display: 'inline-block',
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            backgroundColor: selectedCategory.color || '#6366f1',
                          }}
                          title={`Accent: ${selectedCategory.color}`}
                        />
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', fontFamily: 'ui-monospace, monospace', marginTop: '0.15rem' }}>
                        Slug: <code>{selectedCategory.slug}</code>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button className="btn-sm" onClick={e => openEditModal(selectedCategory, e)}>
                      ✏️ Edit Category
                    </button>
                    <button className="btn-sm btn-danger" onClick={e => promptDeleteCategory(selectedCategory, e)}>
                      🗑️ Delete Category
                    </button>
                  </div>
                </div>

                <p style={{ margin: '1rem 0 0', fontSize: '0.92rem', color: 'var(--text-muted)' }}>
                  {selectedCategory.description || 'No description provided for this category.'}
                </p>

                <div
                  style={{
                    display: 'flex',
                    gap: '1rem',
                    flexWrap: 'wrap',
                    marginTop: '1.25rem',
                    paddingTop: '1rem',
                    borderTop: '1px solid var(--border)',
                    fontSize: '0.8rem',
                    color: 'var(--text-dim)',
                  }}
                >
                  <div>
                    <strong>{assignedCount}</strong> {assignedCount === 1 ? 'Course' : 'Courses'} Assigned
                  </div>
                  <div>•</div>
                  <div>Created: {new Date(selectedCategory.created_at).toLocaleDateString()}</div>
                  {selectedCategory.updated_at && (
                    <>
                      <div>•</div>
                      <div>Updated: {new Date(selectedCategory.updated_at).toLocaleDateString()}</div>
                    </>
                  )}
                </div>
              </div>

              {/* Detail Content */}
              {detailLoading ? (
                <div style={{ padding: '2rem', textAlign: 'center' }}>
                  <div className="spinner" style={{ margin: '0 auto 1rem' }} />
                  <p className="empty-text">Loading assigned courses…</p>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                  {/* Left Column: Currently Assigned Courses */}
                  <div
                    style={{
                      background: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      padding: '1.25rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                      <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
                        Assigned Courses ({categoryDetail?.courses?.length || 0})
                      </h3>
                      <span className="badge badge-admin">Active Links</span>
                    </div>

                    {!categoryDetail?.courses || categoryDetail.courses.length === 0 ? (
                      <div
                        style={{
                          textAlign: 'center',
                          padding: '2rem 1rem',
                          background: 'var(--bg-3)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <span style={{ fontSize: '1.75rem', display: 'block', marginBottom: '0.5rem' }}>📚</span>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>
                          No courses currently linked to this category.
                        </p>
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                          Use the Course Assignment Picker on the right to assign curriculum.
                        </p>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: '420px', overflowY: 'auto' }}>
                        {categoryDetail.courses.map(course => (
                          <div
                            key={course.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '0.75rem 0.85rem',
                              background: 'var(--bg-2)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--radius-sm)',
                              gap: '0.5rem',
                            }}
                          >
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                <span style={{ fontSize: '0.9rem' }}>📖</span>
                                <span
                                  style={{
                                    fontWeight: 600,
                                    fontSize: '0.875rem',
                                    color: 'var(--text)',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                  }}
                                >
                                  {course.title}
                                </span>
                              </div>
                              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem', alignItems: 'center' }}>
                                <span className={`badge ${course.is_published ? 'badge-active' : 'badge-inactive'}`} style={{ fontSize: '0.68rem', padding: '0.1rem 0.35rem' }}>
                                  {course.is_published ? 'Published' : 'Draft'}
                                </span>
                                {course.assigned_at && (
                                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                                    Linked {new Date(course.assigned_at).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                            </div>

                            <button
                              className="btn-sm btn-danger"
                              style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', flexShrink: 0 }}
                              onClick={e => removeSingleCourse(course.id, course.title, e)}
                              title="Unlink course from this category"
                            >
                              ✕ Unlink
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Right Column: Multi-Select Course Assignment Picker */}
                  <div
                    style={{
                      background: 'var(--surface)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      padding: '1.25rem',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.85rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Assign Courses</h3>
                      <button
                        className="btn-primary btn-sm"
                        onClick={saveCourseAssignments}
                        disabled={savingAssignments}
                      >
                        {savingAssignments ? 'Saving…' : 'Save Assignments'}
                      </button>
                    </div>

                    <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', margin: 0 }}>
                      Toggle checkboxes to assign or unassign courses for <strong>{selectedCategory.name}</strong>.
                    </p>

                    {/* Course Search input */}
                    <input
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.85rem', padding: '0.4rem 0.6rem' }}
                      placeholder="Search courses to assign…"
                      value={courseSearch}
                      onChange={e => setCourseSearch(e.target.value)}
                    />

                    {/* Course Checkbox List */}
                    <div
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.45rem',
                        maxHeight: '340px',
                        overflowY: 'auto',
                        paddingRight: '0.25rem',
                      }}
                    >
                      {filteredCourses.length === 0 ? (
                        <p className="empty-text" style={{ padding: '1rem', textAlign: 'center' }}>
                          No curriculum courses found.
                        </p>
                      ) : (
                        filteredCourses.map(course => {
                          const isAssigned = selectedCourseIds.has(course.id);
                          return (
                            <label
                              key={course.id}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.65rem',
                                padding: '0.55rem 0.75rem',
                                background: isAssigned ? 'var(--surface-hover)' : 'var(--bg-3)',
                                border: `1px solid ${isAssigned ? 'var(--primary)' : 'var(--border)'}`,
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                                transition: 'all 0.15s ease',
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={isAssigned}
                                onChange={() => toggleCourseSelection(course.id)}
                                style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                              />
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div
                                  style={{
                                    fontSize: '0.85rem',
                                    fontWeight: isAssigned ? 600 : 500,
                                    color: 'var(--text)',
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                  }}
                                >
                                  {course.title}
                                </div>
                                {course.description && (
                                  <div
                                    style={{
                                      fontSize: '0.72rem',
                                      color: 'var(--text-dim)',
                                      whiteSpace: 'nowrap',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                    }}
                                  >
                                    {course.description}
                                  </div>
                                )}
                              </div>
                              <span
                                className={`badge ${course.is_published ? 'badge-active' : 'badge-inactive'}`}
                                style={{ fontSize: '0.65rem', padding: '0.1rem 0.35rem' }}
                              >
                                {course.is_published ? 'Published' : 'Draft'}
                              </span>
                            </label>
                          );
                        })
                      )}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                        {selectedCourseIds.size} of {allCourses.length} courses selected
                      </span>
                      <button
                        className="btn-primary btn-sm"
                        onClick={saveCourseAssignments}
                        disabled={savingAssignments}
                      >
                        {savingAssignments ? 'Saving…' : 'Save Assignments'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                minHeight: '380px',
                textAlign: 'center',
                padding: '2rem',
              }}
            >
              <div
                style={{
                  width: '72px',
                  height: '72px',
                  borderRadius: '50%',
                  background: 'var(--bg-3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '2.5rem',
                  marginBottom: '1rem',
                  border: '1px solid var(--border)',
                }}
              >
                🏷️
              </div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text)' }}>
                Select a Course Category
              </h3>
              <p style={{ maxWidth: '420px', color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.35rem' }}>
                Choose a category from the master list on the left to inspect its details, assign courses, or edit taxonomy.
              </p>
              <button className="btn-primary" style={{ marginTop: '1.25rem' }} onClick={openCreateModal}>
                + Create New Category
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ================= Create / Edit Category Modal ================= */}
      {modalOpen && (
        <div className="modal-overlay" onClick={() => setModalOpen(false)}>
          <div className="modal-container" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modalMode === 'create' ? 'Add New Course Category 🏷️' : 'Edit Category Details ✏️'}</h3>
              <button className="btn-close" onClick={() => setModalOpen(false)}>✕</button>
            </div>

            <form onSubmit={handleCategorySubmit}>
              <div className="modal-body">
                {formError && (
                  <div
                    style={{
                      padding: '0.6rem 0.85rem',
                      background: 'var(--danger-muted)',
                      border: '1px solid var(--danger)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--danger)',
                      fontSize: '0.85rem',
                    }}
                  >
                    ⚠️ {formError}
                  </div>
                )}

                {/* Category Name */}
                <div className="form-group">
                  <label htmlFor="cat-name" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    Category Name *
                  </label>
                  <input
                    id="cat-name"
                    type="text"
                    required
                    className="form-input"
                    placeholder="e.g. Full-Stack Web Development"
                    value={formData.name}
                    onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  />
                </div>

                {/* Description */}
                <div className="form-group">
                  <label htmlFor="cat-desc" style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    Description (Optional)
                  </label>
                  <textarea
                    id="cat-desc"
                    className="form-input"
                    rows={3}
                    placeholder="Brief description of the subject area or target learning outcomes…"
                    value={formData.description}
                    onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  />
                </div>

                {/* Icon Selection */}
                <div className="form-group">
                  <label style={{ fontWeight: 600, fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Category Icon</span>
                    <span style={{ fontSize: '1rem' }}>{formData.icon}</span>
                  </label>
                  <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                    {ICON_PRESETS.map(icon => (
                      <button
                        key={icon}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, icon }))}
                        style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: '1.15rem',
                          background: formData.icon === icon ? 'var(--primary)' : 'var(--bg-3)',
                          border: `1px solid ${formData.icon === icon ? 'var(--primary)' : 'var(--border)'}`,
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Color Tag Selection */}
                <div className="form-group">
                  <label style={{ fontWeight: 600, fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>Theme Accent Color</span>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: formData.color }}>
                      {formData.color}
                    </span>
                  </label>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                    {COLOR_PRESETS.map(color => (
                      <button
                        key={color.hex}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, color: color.hex }))}
                        style={{
                          width: '30px',
                          height: '30px',
                          borderRadius: '50%',
                          backgroundColor: color.hex,
                          border: formData.color === color.hex ? '3px solid #ffffff' : '1px solid var(--border)',
                          boxShadow: formData.color === color.hex ? '0 0 8px rgba(255,255,255,0.4)' : 'none',
                          cursor: 'pointer',
                        }}
                        title={color.name}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn-ghost" onClick={() => setModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={formSubmitting}>
                  {formSubmitting
                    ? 'Saving…'
                    : modalMode === 'create'
                    ? 'Create Category'
                    : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= Delete Confirmation Modal ================= */}
      {deleteModalOpen && categoryToDelete && (
        <div className="modal-overlay" onClick={() => setDeleteModalOpen(false)}>
          <div className="modal-container" onClick={e => e.stopPropagation()} style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <h3 style={{ color: 'var(--danger)' }}>Confirm Category Deletion 🗑️</h3>
              <button className="btn-close" onClick={() => setDeleteModalOpen(false)}>✕</button>
            </div>

            <div className="modal-body">
              <p style={{ color: 'var(--text)', fontWeight: 600, fontSize: '1rem' }}>
                Are you sure you want to delete &ldquo;{categoryToDelete.name}&rdquo;?
              </p>

              <div
                style={{
                  padding: '0.85rem 1rem',
                  background: 'var(--warning-muted)',
                  border: '1px solid var(--warning)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  color: 'var(--text)',
                }}
              >
                <div style={{ fontWeight: 600, marginBottom: '0.25rem', color: 'var(--warning)' }}>
                  🛡️ Safe Data Protection Notice
                </div>
                Courses linked to this category ({categoryToDelete.course_count || 0} assigned) will become uncategorized,
                but will <strong>NOT</strong> be deleted or corrupted in the platform curriculum.
              </div>
            </div>

            <div className="modal-footer">
              <button type="button" className="btn-ghost" onClick={() => setDeleteModalOpen(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-danger"
                onClick={confirmDeleteCategory}
                disabled={deleting}
              >
                {deleting ? 'Deleting…' : 'Delete Category'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
