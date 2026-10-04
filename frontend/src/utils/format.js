export const money = (n) => `KES ${Number(n || 0).toLocaleString('en-KE', { maximumFractionDigits: 0 })}`;
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' }) : '-');
export const initials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('');
export const greeting = () => {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
};
export const STATUS = {
  draft: ['Draft', ''], submitted: ['Submitted', 'blue'], under_review: ['Under review', 'gold'],
  changes_required: ['Changes required', 'red'], approved: ['Approved', 'green'], rejected: ['Rejected', 'red'],
  enrolled: ['Enrolled', 'green'],
};
export const DAYS = { 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday' };
