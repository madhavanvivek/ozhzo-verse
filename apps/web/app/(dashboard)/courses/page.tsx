'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useRouter } from 'next/navigation';
import {
  GraduationCap,
  Plus,
  Calendar,
  BookOpen,
  FileCheck,
  Award,
  Trash2,
  CheckCircle2,
  Check,
  X,
  Sparkles
} from 'lucide-react';
import { apiClient } from '@/lib/apiClient';

interface CourseSession {
  id: string;
  course_id: string;
  title: string;
  start_time: string;
  end_time: string;
  is_all_day: boolean;
  location?: string | null;
  recurrence_type?: string | null;
  status: 'SCHEDULED' | 'ATTENDED' | 'CANCELLED';
  notes?: string | null;
}

interface CourseAssignment {
  id: string;
  course_id: string;
  title: string;
  description?: string | null;
  due_date: string;
  status: 'PENDING' | 'SUBMITTED' | 'COMPLETED';
}

interface CourseExam {
  id: string;
  course_id: string;
  title: string;
  start_time: string;
  end_time: string;
  location?: string | null;
  status: 'SCHEDULED' | 'COMPLETED' | 'MISSED';
  notes?: string | null;
}

interface Course {
  id: string;
  home_id: string;
  title: string;
  description?: string | null;
  instructor?: string | null;
  provider?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status: 'ACTIVE' | 'COMPLETED' | 'PAUSED' | 'DROPPED';
  color?: string | null;
  sessions?: CourseSession[];
  assignments?: CourseAssignment[];
  exams?: CourseExam[];
}

export default function CoursesPage() {
  const router = useRouter();
  const [activeHomeId, setActiveHomeId] = useState<string | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<'SESSIONS' | 'ASSIGNMENTS' | 'EXAMS'>('SESSIONS');

  // Modals
  const [isAddCourseOpen, setIsAddCourseOpen] = useState(false);
  const [isAddSessionOpen, setIsAddSessionOpen] = useState(false);
  const [isAddAssignmentOpen, setIsAddAssignmentOpen] = useState(false);
  const [isAddExamOpen, setIsAddExamOpen] = useState(false);

  // New Course Form State
  const [courseTitle, setCourseTitle] = useState('');
  const [courseDescription, setCourseDescription] = useState('');
  const [courseInstructor, setCourseInstructor] = useState('');
  const [courseProvider, setCourseProvider] = useState('');
  const [courseStartDate, setCourseStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [courseEndDate, setCourseEndDate] = useState(
    new Date(Date.now() + 86400000 * 90).toISOString().split('T')[0]
  );
  const [courseColor, setCourseColor] = useState('#6366f1');

  // New Session Form State
  const [sessTitle, setSessTitle] = useState('');
  const [sessDate, setSessDate] = useState(new Date().toISOString().split('T')[0]);
  const [sessStartTime, setSessStartTime] = useState('10:00');
  const [sessEndTime, setSessEndTime] = useState('11:30');
  const [sessLocation, setSessLocation] = useState('');
  const [sessRecurrence, setSessRecurrence] = useState('WEEKLY');
  const [sessNotes, setSessNotes] = useState('');

  // New Assignment Form State
  const [assignTitle, setAssignTitle] = useState('');
  const [assignDesc, setAssignDesc] = useState('');
  const [assignDueDate, setAssignDueDate] = useState(
    new Date(Date.now() + 86400000 * 7).toISOString().split('T')[0]
  );

  // New Exam Form State
  const [examTitle, setExamTitle] = useState('');
  const [examDate, setExamDate] = useState(
    new Date(Date.now() + 86400000 * 14).toISOString().split('T')[0]
  );
  const [examStartTime, setExamStartTime] = useState('14:00');
  const [examEndTime, setExamEndTime] = useState('17:00');
  const [examLocation, setExamLocation] = useState('Online Portal / Study Room');
  const [examNotes, setExamNotes] = useState('');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((curr) => (curr === msg ? null : curr));
    }, 4000);
  };

  const loadData = async (selectCourseId?: string) => {
    setIsLoading(true);
    try {
      const homeId = await apiClient.getValidActiveHome();
      setActiveHomeId(homeId);

      if (homeId) {
        const res = await apiClient.get<any>(`/homes/${homeId}/courses`);
        const list: Course[] = Array.isArray(res) ? res : (Array.isArray(res?.items) ? res.items : (Array.isArray(res?.data) ? res.data : []));
        setCourses(list);

        if (list.length > 0) {
          const targetId = selectCourseId || (selectedCourse && list.some(c => c.id === selectedCourse.id) ? selectedCourse.id : list[0].id);
          try {
            const detailRes = await apiClient.get<Course>(`/homes/${homeId}/courses/${targetId}`);
            setSelectedCourse(detailRes);
          } catch {
            const fallback = list.find(c => c.id === targetId) || list[0];
            setSelectedCourse(fallback);
          }
        } else {
          setSelectedCourse(null);
        }
      }
    } catch (err) {
      console.error('Failed to load courses:', err);
      setCourses([]);
      setSelectedCourse(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectCourse = async (courseId: string) => {
    if (!activeHomeId) return;
    try {
      const detailRes = await apiClient.get<Course>(`/homes/${activeHomeId}/courses/${courseId}`);
      setSelectedCourse(detailRes);
    } catch (err) {
      console.error('Failed to load course details:', err);
      const fallback = courses.find(c => c.id === courseId) || null;
      setSelectedCourse(fallback);
    }
  };

  useEffect(() => {
    loadData();

    const handleHomeChanged = () => {
      loadData();
    };
    window.addEventListener('home-changed', handleHomeChanged);
    return () => window.removeEventListener('home-changed', handleHomeChanged);
  }, []);

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !courseTitle.trim()) return;

    try {
      const payload = {
        title: courseTitle.trim(),
        description: courseDescription.trim() || undefined,
        instructor: courseInstructor.trim() || undefined,
        provider: courseProvider.trim() || undefined,
        start_date: courseStartDate || undefined,
        end_date: courseEndDate || undefined,
        status: 'ACTIVE',
        color: courseColor || '#6366f1'
      };

      const res = await apiClient.post<any>(`/homes/${activeHomeId}/courses`, payload);
      const created = res?.data || res;
      showToast(`Course "${payload.title}" created successfully.`);
      setIsAddCourseOpen(false);
      setCourseTitle('');
      setCourseDescription('');
      setCourseInstructor('');
      setCourseProvider('');
      await loadData(created?.id);
    } catch (err: any) {
      console.error('Failed to create course:', err);
      alert(err?.message || 'Failed to create course.');
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !selectedCourse || !sessTitle.trim()) return;

    try {
      const [y, m, d] = sessDate.split('-').map(Number);
      const [sH, sM] = (sessStartTime || '10:00').split(':').map(Number);
      const [eH, eM] = (sessEndTime || '11:30').split(':').map(Number);
      const startDate = new Date(y, m - 1, d, sH, sM, 0);
      let endDate = new Date(y, m - 1, d, eH, eM, 0);
      if (endDate < startDate) {
        endDate = new Date(startDate.getTime() + 3600000);
      }

      const payload = {
        title: sessTitle.trim(),
        start_time: startDate.toISOString(),
        end_time: endDate.toISOString(),
        is_all_day: false,
        location: sessLocation.trim() || undefined,
        recurrence_type: sessRecurrence || 'NONE',
        notes: sessNotes.trim() || undefined,
        status: 'SCHEDULED'
      };

      await apiClient.post(`/homes/${activeHomeId}/courses/${selectedCourse.id}/sessions`, payload);
      showToast(`Class session "${payload.title}" added and projected to calendar.`);
      setIsAddSessionOpen(false);
      setSessTitle('');
      setSessNotes('');
      await loadData(selectedCourse.id);
    } catch (err: any) {
      console.error('Failed to add session:', err);
      alert(err?.message || 'Failed to add session.');
    }
  };

  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !selectedCourse || !assignTitle.trim()) return;

    try {
      const payload = {
        title: assignTitle.trim(),
        description: assignDesc.trim() || undefined,
        due_date: assignDueDate,
        status: 'PENDING'
      };

      await apiClient.post(`/homes/${activeHomeId}/courses/${selectedCourse.id}/assignments`, payload);
      showToast(`Assignment "${payload.title}" added and projected to calendar.`);
      setIsAddAssignmentOpen(false);
      setAssignTitle('');
      setAssignDesc('');
      await loadData(selectedCourse.id);
    } catch (err: any) {
      console.error('Failed to add assignment:', err);
      alert(err?.message || 'Failed to add assignment.');
    }
  };

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeHomeId || !selectedCourse || !examTitle.trim()) return;

    try {
      const [y, m, d] = examDate.split('-').map(Number);
      const [sH, sM] = (examStartTime || '14:00').split(':').map(Number);
      const [eH, eM] = (examEndTime || '17:00').split(':').map(Number);
      const startDate = new Date(y, m - 1, d, sH, sM, 0);
      let endDate = new Date(y, m - 1, d, eH, eM, 0);
      if (endDate < startDate) {
        endDate = new Date(startDate.getTime() + 3600000);
      }

      const payload = {
        title: examTitle.trim(),
        start_time: startDate.toISOString(),
        end_time: endDate.toISOString(),
        location: examLocation.trim() || undefined,
        notes: examNotes.trim() || undefined,
        status: 'SCHEDULED'
      };

      await apiClient.post(`/homes/${activeHomeId}/courses/${selectedCourse.id}/exams`, payload);
      showToast(`Exam "${payload.title}" added and projected to calendar.`);
      setIsAddExamOpen(false);
      setExamTitle('');
      setExamNotes('');
      await loadData(selectedCourse.id);
    } catch (err: any) {
      console.error('Failed to add exam:', err);
      alert(err?.message || 'Failed to add exam.');
    }
  };

  const toggleSessionStatus = async (session: CourseSession) => {
    if (!activeHomeId || !selectedCourse) return;
    const nextStatus = session.status === 'ATTENDED' ? 'SCHEDULED' : 'ATTENDED';
    try {
      await apiClient.patch(`/homes/${activeHomeId}/courses/${selectedCourse.id}/sessions/${session.id}`, {
        status: nextStatus
      });
      showToast(`Session marked as ${nextStatus.toLowerCase()}.`);
      await loadData(selectedCourse.id);
    } catch (err: any) {
      console.error('Failed to update session:', err);
      alert(err?.message || 'Failed to update session.');
    }
  };

  const toggleAssignmentStatus = async (assignment: CourseAssignment) => {
    if (!activeHomeId || !selectedCourse) return;
    const nextStatus = assignment.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED';
    try {
      await apiClient.patch(`/homes/${activeHomeId}/courses/${selectedCourse.id}/assignments/${assignment.id}`, {
        status: nextStatus
      });
      showToast(`Assignment marked as ${nextStatus.toLowerCase()}.`);
      await loadData(selectedCourse.id);
    } catch (err: any) {
      console.error('Failed to update assignment:', err);
      alert(err?.message || 'Failed to update assignment.');
    }
  };

  const toggleExamStatus = async (exam: CourseExam) => {
    if (!activeHomeId || !selectedCourse) return;
    const nextStatus = exam.status === 'COMPLETED' ? 'SCHEDULED' : 'COMPLETED';
    try {
      await apiClient.patch(`/homes/${activeHomeId}/courses/${selectedCourse.id}/exams/${exam.id}`, {
        status: nextStatus
      });
      showToast(`Exam marked as ${nextStatus.toLowerCase()}.`);
      await loadData(selectedCourse.id);
    } catch (err: any) {
      console.error('Failed to update exam:', err);
      alert(err?.message || 'Failed to update exam.');
    }
  };

  const handleDeleteCourse = async (courseId: string) => {
    if (!activeHomeId) return;
    if (!confirm('Are you sure you want to delete this course and its schedule?')) return;
    try {
      await apiClient.delete(`/homes/${activeHomeId}/courses/${courseId}`);
      showToast('Course removed successfully.');
      await loadData();
    } catch (err: any) {
      console.error('Failed to delete course:', err);
      alert(err?.message || 'Failed to delete course.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', maxWidth: '1100px', width: '100%' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          style={{
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            backgroundColor: 'var(--color-primary-900)',
            color: '#ffffff',
            padding: '12px 20px',
            borderRadius: 'var(--radius-md)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
            fontSize: '13px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            zIndex: 9999
          }}
        >
          <Check size={16} color="var(--status-in-stock)" />
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer', marginLeft: '6px' }}
            aria-label="Close notification"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', backgroundColor: '#eef2ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <GraduationCap size={22} color="#4f46e5" />
            </div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-primary-900)', lineHeight: 1.2 }}>
              Learning & Course Planner
            </h1>
          </div>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Track family educational commitments, lessons, assignments, and exam dates with native calendar synchronization.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push('/calendar')}
            style={{ minHeight: '40px', padding: '0 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Calendar size={16} />
            <span>View in Calendar</span>
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsAddCourseOpen(true)}
            style={{ minHeight: '40px', padding: '0 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={16} />
            <span>Add Course</span>
          </Button>
        </div>
      </div>

      {/* Calendar Synchronization Notice */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderLeft: '4px solid #6366f1',
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          fontSize: '13px',
          color: 'var(--color-text-secondary)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Sparkles size={16} color="#6366f1" />
          <span>
            <strong>Dynamic Projection:</strong> All sessions, assignments, and exams automatically project into the Household Calendar agenda and month views in real-time.
          </span>
        </div>
      </div>

      {/* Main Content Layout: Course List + Active Course Detail */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-text-secondary)' }}>
          Loading family courses...
        </div>
      ) : courses.length === 0 ? (
        <Card style={{ padding: '48px', textAlign: 'center' }}>
          <GraduationCap size={48} color="#94a3b8" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
            No courses added yet
          </h3>
          <p style={{ fontSize: '14px', color: 'var(--color-text-secondary)', maxWidth: '460px', margin: '8px auto 20px' }}>
            Keep track of tuition classes, coding bootcamps, school subjects, music lessons, or hobby workshops for everyone in the household.
          </p>
          <Button variant="primary" onClick={() => setIsAddCourseOpen(true)}>
            <Plus size={16} style={{ marginRight: '6px' }} /> Add Your First Course
          </Button>
        </Card>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px', alignItems: 'start' }}>
          {/* Left Column: Courses List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Courses ({courses.length})
              </span>
              <button
                onClick={() => setIsAddCourseOpen(true)}
                style={{ background: 'none', border: 'none', color: 'var(--color-primary-900)', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}
              >
                + Add
              </button>
            </div>

            {courses.map((course) => {
              const isSelected = selectedCourse?.id === course.id;
              const totalSessions = course.sessions?.length || 0;
              const totalAssignments = course.assignments?.length || 0;
              const totalExams = course.exams?.length || 0;

              return (
                <div
                  key={course.id}
                  onClick={() => handleSelectCourse(course.id)}
                  style={{
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    border: `1px solid ${isSelected ? '#6366f1' : 'var(--color-border-subtle)'}`,
                    backgroundColor: isSelected ? '#f5f3ff' : 'var(--color-surface-card)',
                    boxShadow: isSelected ? '0 2px 8px rgba(99, 102, 241, 0.15)' : 'none',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                    <h3 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary-900)', lineHeight: 1.3 }}>
                      {course.title}
                    </h3>
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '6px',
                        backgroundColor: course.status === 'ACTIVE' ? '#ecfdf5' : '#f1f5f9',
                        color: course.status === 'ACTIVE' ? '#047857' : '#64748b'
                      }}
                    >
                      {course.status}
                    </span>
                  </div>

                  {course.instructor && (
                    <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                      👨‍🏫 {course.instructor}
                    </p>
                  )}

                  <div style={{ display: 'flex', gap: '10px', marginTop: '10px', fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                    <span>{totalSessions} Classes</span>
                    <span>•</span>
                    <span>{totalAssignments} Assignments</span>
                    <span>•</span>
                    <span>{totalExams} Exams</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Right Column: Active Course Management Card */}
          {selectedCourse && (
            <Card style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '16px' }}>
                <div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                    {selectedCourse.title}
                  </h2>
                  {selectedCourse.description && (
                    <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
                      {selectedCourse.description}
                    </p>
                  )}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', marginTop: '8px', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    {selectedCourse.instructor && <span><strong>Instructor:</strong> {selectedCourse.instructor}</span>}
                    {selectedCourse.provider && <span><strong>Platform/School:</strong> {selectedCourse.provider}</span>}
                    {selectedCourse.start_date && <span><strong>Duration:</strong> {selectedCourse.start_date} to {selectedCourse.end_date || 'Ongoing'}</span>}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <Button
                    size="sm"
                    variant="destructive"
                    onClick={() => handleDeleteCourse(selectedCourse.id)}
                    style={{ minHeight: '34px', padding: '0 10px' }}
                    aria-label="Delete course"
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>

              {/* Submodule Tabs: Sessions / Assignments / Exams */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '8px' }}>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => setActiveTab('SESSIONS')}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 'var(--radius-md)',
                      border: 'none',
                      backgroundColor: activeTab === 'SESSIONS' ? '#6366f1' : 'transparent',
                      color: activeTab === 'SESSIONS' ? '#ffffff' : 'var(--color-text-secondary)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <BookOpen size={14} />
                    <span>Classes & Sessions ({selectedCourse.sessions?.length || 0})</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('ASSIGNMENTS')}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 'var(--radius-md)',
                      border: 'none',
                      backgroundColor: activeTab === 'ASSIGNMENTS' ? '#6366f1' : 'transparent',
                      color: activeTab === 'ASSIGNMENTS' ? '#ffffff' : 'var(--color-text-secondary)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <FileCheck size={14} />
                    <span>Assignments ({selectedCourse.assignments?.length || 0})</span>
                  </button>

                  <button
                    onClick={() => setActiveTab('EXAMS')}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 'var(--radius-md)',
                      border: 'none',
                      backgroundColor: activeTab === 'EXAMS' ? '#6366f1' : 'transparent',
                      color: activeTab === 'EXAMS' ? '#ffffff' : 'var(--color-text-secondary)',
                      fontWeight: 600,
                      fontSize: '13px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <Award size={14} />
                    <span>Exams & Tests ({selectedCourse.exams?.length || 0})</span>
                  </button>
                </div>

                <div>
                  {activeTab === 'SESSIONS' && (
                    <Button size="sm" variant="primary" onClick={() => setIsAddSessionOpen(true)} style={{ minHeight: '34px', padding: '0 12px' }}>
                      <Plus size={14} style={{ marginRight: '4px' }} /> Add Class Session
                    </Button>
                  )}
                  {activeTab === 'ASSIGNMENTS' && (
                    <Button size="sm" variant="primary" onClick={() => setIsAddAssignmentOpen(true)} style={{ minHeight: '34px', padding: '0 12px' }}>
                      <Plus size={14} style={{ marginRight: '4px' }} /> Add Assignment
                    </Button>
                  )}
                  {activeTab === 'EXAMS' && (
                    <Button size="sm" variant="primary" onClick={() => setIsAddExamOpen(true)} style={{ minHeight: '34px', padding: '0 12px' }}>
                      <Plus size={14} style={{ marginRight: '4px' }} /> Add Exam
                    </Button>
                  )}
                </div>
              </div>

              {/* Tab 1: Sessions List */}
              {activeTab === 'SESSIONS' && (
                <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {!selectedCourse.sessions || selectedCourse.sessions.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                      No class sessions scheduled. Add a session to see it in your Household Calendar.
                    </div>
                  ) : (
                    selectedCourse.sessions.map((sess) => {
                      const isAttended = sess.status === 'ATTENDED';
                      const startDt = new Date(sess.start_time);
                      const timeStr = startDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                      const dateStr = startDt.toLocaleDateString([], { month: 'short', day: 'numeric', weekday: 'short' });

                      return (
                        <div
                          key={sess.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '12px 16px',
                            backgroundColor: isAttended ? '#f8fafc' : '#ffffff',
                            border: '1px solid var(--color-border-subtle)',
                            borderRadius: 'var(--radius-md)',
                            borderLeft: `4px solid ${isAttended ? '#10b981' : '#6366f1'}`
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <button
                              onClick={() => toggleSessionStatus(sess)}
                              style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                padding: '2px',
                                color: isAttended ? '#10b981' : 'var(--color-text-tertiary)'
                              }}
                              aria-label={isAttended ? 'Mark uncompleted' : 'Mark completed'}
                            >
                              <CheckCircle2 size={20} />
                            </button>
                            <div>
                              <h4 style={{ fontSize: '14px', fontWeight: 600, color: isAttended ? 'var(--color-text-secondary)' : 'var(--color-primary-900)', textDecoration: isAttended ? 'line-through' : 'none' }}>
                                {sess.title}
                              </h4>
                              <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                                <span>📅 {dateStr} at {timeStr}</span>
                                {sess.location && <span>📍 {sess.location}</span>}
                                {sess.recurrence_type && sess.recurrence_type !== 'NONE' && <span>🔁 {sess.recurrence_type}</span>}
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px', backgroundColor: isAttended ? '#ecfdf5' : '#eef2ff', color: isAttended ? '#047857' : '#4338ca' }}>
                              {sess.status}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}

              {/* Tab 2: Assignments List */}
              {activeTab === 'ASSIGNMENTS' && (
                <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {!selectedCourse.assignments || selectedCourse.assignments.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                      No assignments added. Keep track of homework, projects, and deadlines here.
                    </div>
                  ) : (
                    selectedCourse.assignments.map((assign) => {
                      const isCompleted = assign.status === 'COMPLETED' || assign.status === 'SUBMITTED';
                      return (
                        <div
                          key={assign.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '12px 16px',
                            backgroundColor: isCompleted ? '#f8fafc' : '#ffffff',
                            border: '1px solid var(--color-border-subtle)',
                            borderRadius: 'var(--radius-md)',
                            borderLeft: `4px solid ${isCompleted ? '#10b981' : '#f59e0b'}`
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <button
                              onClick={() => toggleAssignmentStatus(assign)}
                              style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                padding: '2px',
                                color: isCompleted ? '#10b981' : 'var(--color-text-tertiary)'
                              }}
                              aria-label={isCompleted ? 'Mark uncompleted' : 'Mark completed'}
                            >
                              <CheckCircle2 size={20} />
                            </button>
                            <div>
                              <h4 style={{ fontSize: '14px', fontWeight: 600, color: isCompleted ? 'var(--color-text-secondary)' : 'var(--color-primary-900)', textDecoration: isCompleted ? 'line-through' : 'none' }}>
                                {assign.title}
                              </h4>
                              <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                                <span>⏰ Due: {assign.due_date}</span>
                                {assign.description && <span>{assign.description}</span>}
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px', backgroundColor: isCompleted ? '#ecfdf5' : '#fffbeb', color: isCompleted ? '#047857' : '#b45309' }}>
                              {assign.status}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}

              {/* Tab 3: Exams List */}
              {activeTab === 'EXAMS' && (
                <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {!selectedCourse.exams || selectedCourse.exams.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '30px', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                      No exams or tests scheduled.
                    </div>
                  ) : (
                    selectedCourse.exams.map((ex) => {
                      const isCompleted = ex.status === 'COMPLETED';
                      const startDt = new Date(ex.start_time);
                      const timeStr = startDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                      const dateStr = startDt.toLocaleDateString([], { month: 'short', day: 'numeric', weekday: 'short' });

                      return (
                        <div
                          key={ex.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '12px 16px',
                            backgroundColor: isCompleted ? '#f8fafc' : '#ffffff',
                            border: '1px solid var(--color-border-subtle)',
                            borderRadius: 'var(--radius-md)',
                            borderLeft: `4px solid ${isCompleted ? '#10b981' : '#ef4444'}`
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <button
                              onClick={() => toggleExamStatus(ex)}
                              style={{
                                background: 'none',
                                border: 'none',
                                cursor: 'pointer',
                                padding: '2px',
                                color: isCompleted ? '#10b981' : 'var(--color-text-tertiary)'
                              }}
                              aria-label={isCompleted ? 'Mark uncompleted' : 'Mark completed'}
                            >
                              <CheckCircle2 size={20} />
                            </button>
                            <div>
                              <h4 style={{ fontSize: '14px', fontWeight: 600, color: isCompleted ? 'var(--color-text-secondary)' : 'var(--color-primary-900)' }}>
                                {ex.title}
                              </h4>
                              <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                                <span>📝 {dateStr} at {timeStr}</span>
                                {ex.location && <span>📍 {ex.location}</span>}
                              </div>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 600, padding: '2px 8px', borderRadius: '12px', backgroundColor: isCompleted ? '#ecfdf5' : '#fef2f2', color: isCompleted ? '#047857' : '#b91c1c' }}>
                              {ex.status}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* Add Course Modal */}
      {isAddCourseOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAddCourseOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '520px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Add Learning Course / Subject
              </h3>
              <button
                onClick={() => setIsAddCourseOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close"
              >
                <X size={18} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleCreateCourse} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Course Title *
                </label>
                <Input
                  required
                  placeholder="e.g. Python Programming Masterclass, Grade 10 Math, Guitar Lessons"
                  value={courseTitle}
                  onChange={(e) => setCourseTitle(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Instructor / Teacher
                  </label>
                  <Input
                    placeholder="e.g. Dr. Angela, Mr. Sharma"
                    value={courseInstructor}
                    onChange={(e) => setCourseInstructor(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Platform / School
                  </label>
                  <Input
                    placeholder="e.g. Coursera, City Academy, Zoom"
                    value={courseProvider}
                    onChange={(e) => setCourseProvider(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Start Date
                  </label>
                  <Input
                    type="date"
                    value={courseStartDate}
                    onChange={(e) => setCourseStartDate(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    End Date
                  </label>
                  <Input
                    type="date"
                    value={courseEndDate}
                    onChange={(e) => setCourseEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Description / Goals
                </label>
                <Input
                  placeholder="e.g. Weekly classes on Tuesdays and Thursdays covering core programming"
                  value={courseDescription}
                  onChange={(e) => setCourseDescription(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '6px' }}>
                  Color Tag
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  {['#6366f1', '#059669', '#d97706', '#dc2626', '#8b5cf6', '#0284c7'].map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setCourseColor(c)}
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        backgroundColor: c,
                        border: courseColor === c ? '3px solid #0f172a' : '2px solid transparent',
                        cursor: 'pointer'
                      }}
                    />
                  ))}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <Button type="button" variant="secondary" onClick={() => setIsAddCourseOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Create Course
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Session Modal */}
      {isAddSessionOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAddSessionOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Schedule Class / Training Session
              </h3>
              <button
                onClick={() => setIsAddSessionOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close"
              >
                <X size={18} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleCreateSession} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Session Topic / Class Name *
                </label>
                <Input
                  required
                  placeholder="e.g. Live Coding: Functions and Loops"
                  value={sessTitle}
                  onChange={(e) => setSessTitle(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Date *
                  </label>
                  <Input
                    type="date"
                    required
                    value={sessDate}
                    onChange={(e) => setSessDate(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Start Time
                  </label>
                  <Input
                    type="time"
                    value={sessStartTime}
                    onChange={(e) => setSessStartTime(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    End Time
                  </label>
                  <Input
                    type="time"
                    value={sessEndTime}
                    onChange={(e) => setSessEndTime(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Location / Link
                  </label>
                  <Input
                    placeholder="e.g. Zoom Room / Study Desk"
                    value={sessLocation}
                    onChange={(e) => setSessLocation(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Recurrence
                  </label>
                  <select
                    value={sessRecurrence}
                    onChange={(e) => setSessRecurrence(e.target.value)}
                    style={{
                      width: '100%',
                      height: '42px',
                      padding: '0 10px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border-subtle)',
                      backgroundColor: 'var(--color-surface-subtle)',
                      fontSize: '13px'
                    }}
                  >
                    <option value="NONE">Does not repeat</option>
                    <option value="DAILY">Daily</option>
                    <option value="WEEKLY">Weekly</option>
                    <option value="MONTHLY">Monthly</option>
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Preparation Notes / Materials
                </label>
                <Input
                  placeholder="e.g. Bring textbook chapter 4, install VSCode"
                  value={sessNotes}
                  onChange={(e) => setSessNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <Button type="button" variant="secondary" onClick={() => setIsAddSessionOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Save Session
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Assignment Modal */}
      {isAddAssignmentOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAddAssignmentOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Add Course Assignment
              </h3>
              <button
                onClick={() => setIsAddAssignmentOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close"
              >
                <X size={18} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleCreateAssignment} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Assignment Title *
                </label>
                <Input
                  required
                  placeholder="e.g. Build Calculator App, Essay Submission"
                  value={assignTitle}
                  onChange={(e) => setAssignTitle(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Due Date *
                </label>
                <Input
                  type="date"
                  required
                  value={assignDueDate}
                  onChange={(e) => setAssignDueDate(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Description / Submission Instructions
                </label>
                <Input
                  placeholder="e.g. Submit GitHub repository link or PDF to classroom"
                  value={assignDesc}
                  onChange={(e) => setAssignDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <Button type="button" variant="secondary" onClick={() => setIsAddAssignmentOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Save Assignment
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Exam Modal */}
      {isAddExamOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px'
          }}
          onClick={() => setIsAddExamOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: '#ffffff',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-900)' }}>
                Add Exam / Test Schedule
              </h3>
              <button
                onClick={() => setIsAddExamOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}
                aria-label="Close"
              >
                <X size={18} color="var(--color-text-secondary)" />
              </button>
            </div>

            <form onSubmit={handleCreateExam} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Exam Title *
                </label>
                <Input
                  required
                  placeholder="e.g. Midterm Practical Exam, Final Certification Exam"
                  value={examTitle}
                  onChange={(e) => setExamTitle(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Exam Date *
                  </label>
                  <Input
                    type="date"
                    required
                    value={examDate}
                    onChange={(e) => setExamDate(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    Start Time
                  </label>
                  <Input
                    type="time"
                    value={examStartTime}
                    onChange={(e) => setExamStartTime(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                    End Time
                  </label>
                  <Input
                    type="time"
                    value={examEndTime}
                    onChange={(e) => setExamEndTime(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Exam Location / Link
                </label>
                <Input
                  placeholder="e.g. City School Hall B / Online Proctored Portal"
                  value={examLocation}
                  onChange={(e) => setExamLocation(e.target.value)}
                />
              </div>

              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: '4px' }}>
                  Notes / Syllabus
                </label>
                <Input
                  placeholder="e.g. Timed 180 min exam. Chapters 1-8"
                  value={examNotes}
                  onChange={(e) => setExamNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <Button type="button" variant="secondary" onClick={() => setIsAddExamOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary">
                  Save Exam
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
