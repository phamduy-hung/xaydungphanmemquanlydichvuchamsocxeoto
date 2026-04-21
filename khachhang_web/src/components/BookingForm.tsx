import React, { useEffect, useRef, useState } from 'react';

const SERVICES = [
  'Rửa xe thường',
  'Rửa xe + hút bụi',
  'Phủ ceramic nhanh',
  'Phủ ceramic cao cấp',
  'Vệ sinh nội thất',
  'Vệ sinh khoang máy',
  'Bảo dưỡng tổng quát',
  'Thay dầu máy',
  'Sửa chữa điện',
  'Khác',
];

interface BookingFormData {
  ho_ten: string;
  sdt: string;
  bien_so: string;
  dich_vu: string;
  ngay_hen: string;
  gio_hen: string;
  ghi_chu: string;
}

// Dev: dùng Vite proxy (/api -> 127.0.0.1:8765) để ổn định kết nối.
// Prod/LAN: có thể override bằng VITE_API_BASE_URL.
const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL as string | undefined) || '/api';

export const BookingForm: React.FC = () => {
  const calendarWrapRef = useRef<HTMLDivElement>(null);
  const [form, setForm] = useState<BookingFormData>({
    ho_ten: '',
    sdt: '',
    bien_so: '',
    dich_vu: '',
    ngay_hen: '',
    gio_hen: '',
    ghi_chu: '',
  });

  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [showCalendar, setShowCalendar] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState<Date>(new Date());

  const formatDisplayDate = (d: Date): string => {
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = String(d.getFullYear());
    return `${dd}/${mm}/${yyyy}`;
  };

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (!calendarWrapRef.current) return;
      if (!calendarWrapRef.current.contains(e.target as Node)) {
        setShowCalendar(false);
      }
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.ho_ten.trim() || !form.sdt.trim()) {
      setErrorMsg('Vui lòng nhập đầy đủ Họ tên và Số điện thoại.');
      setStatus('error');
      return;
    }
    setStatus('loading');
    setErrorMsg('');

    try {
      const res = await fetch(`${API_BASE}/booking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (data.success) {
        setStatus('success');
        setForm({ ho_ten: '', sdt: '', bien_so: '', dich_vu: '', ngay_hen: '', gio_hen: '', ghi_chu: '' });
      } else {
        setErrorMsg(data.error || 'Đã có lỗi xảy ra. Vui lòng thử lại.');
        setStatus('error');
      }
    } catch (err: any) {
      setErrorMsg('Không kết nối được tới máy chủ. Vui lòng kiểm tra API server (port 8765).');
      setStatus('error');
    }
  };

  const inputClass =
    'w-full bg-background/50 border border-border rounded-xl px-4 py-3 text-foreground placeholder-foreground/50 focus:outline-none focus:border-cyan-500/60 transition-all duration-300 backdrop-blur-sm text-sm';
  const labelClass = 'block text-foreground/70 text-xs font-medium mb-1.5 uppercase tracking-wider';
  const weekDays = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];
  const monthLabel = `Tháng ${calendarMonth.getMonth() + 1}/${calendarMonth.getFullYear()}`;
  const firstDayOfMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
  const firstWeekDay = (firstDayOfMonth.getDay() + 6) % 7;
  const daysInMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0).getDate();
  const calendarCells: Array<Date | null> = [];
  for (let i = 0; i < firstWeekDay; i++) calendarCells.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    calendarCells.push(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), d));
  }

  return (
    <section id="booking" className="relative z-10 w-full py-24 px-6 md:px-12 lg:px-16">
      {/* Section heading */}
      <div className="max-w-3xl mx-auto text-center mb-14">
        <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-foreground/70 border border-border rounded-full px-4 py-2 mb-6 liquid-glass">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse inline-block shadow-[0_0_8px_rgba(6,182,212,0.6)]" />
          Đặt lịch trực tuyến
        </div>
        <h2
          className="text-4xl md:text-5xl lg:text-6xl font-normal mb-4 text-foreground"
          style={{ letterSpacing: '-0.03em' }}
        >
          Đặt lịch <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">chăm sóc xe</span>
        </h2>
        <p className="text-foreground/60 text-lg">
          Điền thông tin bên dưới — đội ngũ chúng tôi sẽ liên hệ xác nhận trong vòng 30 phút.
        </p>
      </div>

      {/* Card Form */}
      <div className="max-w-2xl mx-auto liquid-glass border border-white/5 rounded-2xl p-8 md:p-10 shadow-2xl relative overflow-hidden">
        {/* subtle gradient glow behind the form inside the card */}
        <div className="absolute inset-x-0 -top-40 h-80 bg-cyan-500/10 blur-[100px] pointer-events-none" />

        {status === 'success' ? (
          <div className="text-center py-10 relative z-10">
            <h3 className="text-3xl font-semibold text-foreground mb-3 mt-4">Đặt lịch thành công!</h3>
            <p className="text-foreground/60 mb-8">
              Chúng tôi đã nhận được yêu cầu của bạn và sẽ liên hệ xác nhận sớm nhất có thể.
            </p>
            <button
              onClick={() => setStatus('idle')}
              className="bg-foreground text-background px-8 py-3 rounded-xl font-medium hover:opacity-90 transition-opacity"
            >
              Đặt lịch tiếp
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5 relative z-10">
            {/* Row 1: Tên + SĐT */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Họ và tên *</label>
                <input
                  type="text"
                  name="ho_ten"
                  value={form.ho_ten}
                  onChange={handleChange}
                  placeholder="Nguyễn Văn A"
                  className={inputClass}
                  required
                />
              </div>
              <div>
                <label className={labelClass}>Số điện thoại *</label>
                <input
                  type="tel"
                  name="sdt"
                  value={form.sdt}
                  onChange={handleChange}
                  placeholder="0901 234 567"
                  className={inputClass}
                  required
                />
              </div>
            </div>

            {/* Row 2: Biển số + Dịch vụ */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Biển số xe</label>
                <input
                  type="text"
                  name="bien_so"
                  value={form.bien_so}
                  onChange={handleChange}
                  placeholder="51A-12345"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Dịch vụ</label>
                <select
                  name="dich_vu"
                  value={form.dich_vu}
                  onChange={handleChange}
                  className={`${inputClass} cursor-pointer [&>option]:bg-background`}
                >
                  <option value="">Chọn dịch vụ...</option>
                  {SERVICES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Row 3: Ngày + Giờ */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Ngày hẹn</label>
                <div className="relative" ref={calendarWrapRef}>
                  <input
                    type="text"
                    name="ngay_hen"
                    value={form.ngay_hen}
                    onChange={handleChange}
                    placeholder="dd/mm/yyyy"
                    className={`${inputClass} cursor-pointer`}
                    onFocus={() => setShowCalendar(true)}
                    onClick={() => setShowCalendar(true)}
                  />
                  {showCalendar && (
                    <div className="absolute z-50 mt-2 w-full rounded-xl border border-border bg-[#0f172a] p-3 shadow-2xl">
                      <div className="mb-2 flex items-center justify-between text-sm">
                        <button
                          type="button"
                          className="rounded-md px-2 py-1 hover:bg-white/10"
                          onClick={() =>
                            setCalendarMonth(
                              new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1)
                            )
                          }
                        >
                          ‹
                        </button>
                        <span className="font-semibold text-foreground">{monthLabel}</span>
                        <button
                          type="button"
                          className="rounded-md px-2 py-1 hover:bg-white/10"
                          onClick={() =>
                            setCalendarMonth(
                              new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1)
                            )
                          }
                        >
                          ›
                        </button>
                      </div>
                      <div className="grid grid-cols-7 gap-1 text-center text-xs text-foreground/70">
                        {weekDays.map((d) => (
                          <div key={d} className="py-1">{d}</div>
                        ))}
                      </div>
                      <div className="mt-1 grid grid-cols-7 gap-1">
                        {calendarCells.map((d, idx) =>
                          d ? (
                            <button
                              key={`${d.toISOString()}-${idx}`}
                              type="button"
                              className="rounded-md py-2 text-sm text-foreground hover:bg-cyan-500/30"
                              onClick={() => {
                                setForm((prev) => ({ ...prev, ngay_hen: formatDisplayDate(d) }));
                                setShowCalendar(false);
                              }}
                            >
                              {d.getDate()}
                            </button>
                          ) : (
                            <div key={`empty-${idx}`} />
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <div>
                <label className={labelClass}>Giờ hẹn</label>
                <input
                  type="text"
                  name="gio_hen"
                  value={form.gio_hen}
                  onChange={handleChange}
                  placeholder="Nhập giờ hẹn"
                  className={inputClass}
                />
              </div>
            </div>

            {/* Row 4: Ghi chú */}
            <div>
              <label className={labelClass}>Ghi chú thêm</label>
              <textarea
                name="ghi_chu"
                value={form.ghi_chu}
                onChange={handleChange}
                placeholder="Xe bị trầy xước, cần kiểm tra thêm bộ phận..."
                rows={3}
                className={`${inputClass} resize-none`}
              />
            </div>

            {/* Error */}
            {status === 'error' && errorMsg && (
              <div className="bg-destructive/10 border border-destructive/30 text-destructive text-sm rounded-xl px-4 py-3">
                ⚠️ {errorMsg}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={status === 'loading'}
              className="w-full bg-foreground text-background font-semibold py-4 rounded-xl text-sm hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed mt-2 shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_25px_rgba(255,255,255,0.2)]"
            >
              {status === 'loading' ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10" strokeWidth="4" className="opacity-25" />
                    <path d="M4 12a8 8 0 018-8" strokeWidth="4" />
                  </svg>
                  Đang gửi...
                </span>
              ) : 'Xác nhận đặt lịch'}
            </button>

            <p className="text-center text-foreground/40 text-xs">
              Bằng cách đặt lịch, bạn đồng ý để chúng tôi liên hệ xác nhận qua số điện thoại đã cung cấp.
            </p>
          </form>
        )}
      </div>
    </section>
  );
};
