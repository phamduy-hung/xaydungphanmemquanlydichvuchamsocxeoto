import React, { useState } from 'react';

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

const API_URL = 'http://localhost:8765/api/booking';

export const BookingForm: React.FC = () => {
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
      const res = await fetch(API_URL, {
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
    } catch {
      setErrorMsg('Không kết nối được tới máy chủ. Vui lòng thử lại sau.');
      setStatus('error');
    }
  };

  const inputClass =
    'w-full bg-black/40 border border-white/20 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-white/60 transition-all duration-300 backdrop-blur-sm text-sm';
  const labelClass = 'block text-gray-400 text-xs font-medium mb-1.5 uppercase tracking-wider';

  return (
    <section id="booking" className="relative z-10 w-full py-24 px-6 md:px-12 lg:px-16">
      {/* Section heading */}
      <div className="max-w-3xl mx-auto text-center mb-14">
        <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-gray-400 border border-white/10 rounded-full px-4 py-2 mb-6 liquid-glass">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse inline-block" />
          Đặt lịch trực tuyến
        </div>
        <h2
          className="text-4xl md:text-5xl lg:text-6xl font-normal mb-4 text-white"
          style={{ letterSpacing: '-0.03em' }}
        >
          Đặt lịch <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-indigo-400">chăm sóc xe</span>
        </h2>
        <p className="text-gray-400 text-lg">
          Điền thông tin bên dưới — đội ngũ chúng tôi sẽ liên hệ xác nhận trong vòng 30 phút.
        </p>
      </div>

      {/* Card Form */}
      <div className="max-w-2xl mx-auto liquid-glass border border-white/10 rounded-2xl p-8 md:p-10">
        {status === 'success' ? (
          <div className="text-center py-10">
            <div className="text-6xl mb-4">🎉</div>
            <h3 className="text-2xl font-semibold text-white mb-3">Đặt lịch thành công!</h3>
            <p className="text-gray-400 mb-8">
              Chúng tôi đã nhận được yêu cầu của bạn và sẽ liên hệ xác nhận sớm nhất có thể.
            </p>
            <button
              onClick={() => setStatus('idle')}
              className="bg-white text-black px-8 py-3 rounded-xl font-medium hover:bg-gray-100 transition-colors"
            >
              Đặt lịch tiếp
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
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
                  className={`${inputClass} cursor-pointer`}
                >
                  <option value="" className="bg-gray-900">Chọn dịch vụ...</option>
                  {SERVICES.map(s => (
                    <option key={s} value={s} className="bg-gray-900">{s}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Row 3: Ngày + Giờ */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className={labelClass}>Ngày hẹn</label>
                <input
                  type="date"
                  name="ngay_hen"
                  value={form.ngay_hen}
                  onChange={handleChange}
                  className={`${inputClass} [color-scheme:dark]`}
                />
              </div>
              <div>
                <label className={labelClass}>Giờ hẹn</label>
                <input
                  type="time"
                  name="gio_hen"
                  value={form.gio_hen}
                  onChange={handleChange}
                  className={`${inputClass} [color-scheme:dark]`}
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
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3">
                ⚠️ {errorMsg}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={status === 'loading'}
              className="w-full bg-white text-black font-semibold py-4 rounded-xl text-sm hover:bg-gray-100 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {status === 'loading' ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10" strokeWidth="4" className="opacity-25" />
                    <path d="M4 12a8 8 0 018-8" strokeWidth="4" />
                  </svg>
                  Đang gửi...
                </span>
              ) : '🚗  Xác nhận đặt lịch'}
            </button>

            <p className="text-center text-gray-600 text-xs">
              Bằng cách đặt lịch, bạn đồng ý để chúng tôi liên hệ xác nhận qua số điện thoại đã cung cấp.
            </p>
          </form>
        )}
      </div>
    </section>
  );
};
