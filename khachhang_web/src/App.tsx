import React, { useState, useEffect, useRef } from 'react';

// ─── Types ───────────────────────────────────────
const SERVICES = [
  { id: 'rua-xe', label: 'Rửa xe chuyên nghiệp', icon: '🚿' },
  { id: 'hut-bui', label: 'Hút bụi nội thất', icon: '🌀' },
  { id: 'ceramic', label: 'Phủ Ceramic cao cấp', icon: '💎' },
  { id: 'bao-duong', label: 'Bảo dưỡng tổng quát', icon: '🔧' },
  { id: 've-sinh', label: 'Vệ sinh nội thất', icon: '🪟' },
  { id: 'khoang-may', label: 'Vệ sinh khoang máy', icon: '⚙️' },
  { id: 'thay-dau', label: 'Thay dầu máy', icon: '🛢️' },
  { id: 'sua-chua', label: 'Sửa chữa điện tử', icon: '🔌' },
  { id: 'khac', label: 'Khác', icon: '📋' },
];

interface FormData {
  ho_ten: string;
  sdt: string;
  bien_so: string;
  dich_vu: string;
  ngay_hen: string;
  gio_hen: string;
  ghi_chu: string;
}

// ─── Navbar ──────────────────────────────────────
const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  const links = [
    { href: '#home', label: 'Trang chủ' },
    { href: '#services', label: 'Dịch vụ' },
    { href: '#about', label: 'Về chúng tôi' },
    { href: '#booking', label: 'Đặt lịch' },
  ];

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-500 ${
        scrolled ? 'bg-[#0a0a0a]/95 backdrop-blur-xl border-b border-white/5' : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-10 flex items-center justify-between h-18 py-4">
        {/* Logo */}
        <a href="#home" className="flex items-center gap-3 group">
          <img
            src="/logo.png"
            alt="Car Care Logo"
            className="h-14 w-auto object-contain group-hover:scale-105 transition-transform duration-200"
          />
        </a>

        {/* Desktop links */}
        <nav className="hidden md:flex items-center gap-8">
          {links.map(l => (
            <a
              key={l.href}
              href={l.href}
              className="text-gray-400 text-sm font-medium hover:text-white transition-colors duration-200 relative group"
            >
              {l.label}
              <span className="absolute -bottom-0.5 left-0 w-0 h-px bg-cyan-400 group-hover:w-full transition-all duration-300" />
            </a>
          ))}
        </nav>

        {/* CTA */}
        <div className="flex items-center gap-3">
          <a
            href="tel:1900xxxx"
            className="hidden md:flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <span>📞</span>
            <span>1900 xxxx</span>
          </a>
          <a
            href="#booking"
            className="bg-gradient-to-r from-cyan-500 to-sky-500 text-white px-5 py-2.5 rounded-full text-sm font-semibold hover:opacity-90 hover:scale-105 transition-all duration-200 shadow-lg shadow-cyan-500/20"
          >
            Đặt lịch ngay
          </a>
          {/* Mobile menu btn */}
          <button
            className="md:hidden text-gray-400 hover:text-white"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              }
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="md:hidden bg-[#0f0f0f] border-t border-white/5 px-6 py-4 flex flex-col gap-4">
          {links.map(l => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setMenuOpen(false)}
              className="text-gray-300 text-sm py-2 border-b border-white/5"
            >
              {l.label}
            </a>
          ))}
        </div>
      )}
    </header>
  );
};

// ─── Hero ─────────────────────────────────────────
const Hero: React.FC = () => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(t);
  }, []);

  return (
    <section id="home" className="relative min-h-screen flex items-center overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0">
        <video
          className="absolute inset-0 w-full h-full object-cover"
          autoPlay loop muted playsInline
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260403_050628_c4e32401-fab4-4a27-b7a8-6e9291cd5959.mp4"
        />
        {/* Dark overlay optimized for readability */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-black/20" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0a] via-transparent to-transparent" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-10 pt-24 pb-16 w-full">
        <div className="max-w-3xl">
          {/* Badge */}
          <div
            className={`inline-flex items-center gap-2 glass rounded-full px-4 py-2 mb-8 transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
            style={{ transitionDelay: '100ms' }}
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse inline-block" />
            <span className="text-cyan-400 text-xs font-semibold uppercase tracking-widest">Đang nhận đặt lịch hôm nay</span>
          </div>

          {/* Heading */}
          <h1
            className={`text-5xl md:text-7xl lg:text-8xl font-black leading-none mb-6 transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
            style={{ transitionDelay: '200ms', letterSpacing: '-0.04em' }}
          >
            <span className="text-white">Chăm sóc xe</span>
            <br />
            <span className="text-gradient">đẳng cấp</span>
            <br />
            <span className="text-white text-4xl md:text-5xl lg:text-6xl font-bold">chuyên nghiệp.</span>
          </h1>

          {/* Description */}
          <p
            className={`text-gray-300 text-lg md:text-xl max-w-xl mb-10 leading-relaxed transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
            style={{ transitionDelay: '400ms' }}
          >
            Trung tâm chăm sóc xe ô tô hàng đầu. Đội ngũ kỹ thuật viên tay nghề cao, thiết bị hiện đại, cam kết chất lượng từng dịch vụ.
          </p>

          {/* Buttons */}
          <div
            className={`flex flex-wrap gap-4 mb-16 transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
            style={{ transitionDelay: '600ms' }}
          >
            <a
              href="#booking"
              className="bg-gradient-to-r from-cyan-500 to-sky-500 text-white px-8 py-4 rounded-full font-bold text-base hover:opacity-90 hover:scale-105 transition-all shadow-xl shadow-cyan-500/30"
            >
              🗓️ Đặt lịch ngay
            </a>
            <a
              href="#services"
              className="glass border border-white/10 text-white px-8 py-4 rounded-full font-semibold text-base hover:border-white/30 hover:bg-white/10 transition-all"
            >
              Xem dịch vụ →
            </a>
          </div>

          {/* Stats */}
          <div
            className={`flex flex-wrap gap-8 transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
            style={{ transitionDelay: '800ms' }}
          >
            {[
              { num: '5,000+', label: 'Xe đã phục vụ' },
              { num: '8 năm', label: 'Kinh nghiệm' },
              { num: '99%', label: 'Khách hài lòng' },
            ].map(s => (
              <div key={s.label}>
                <div className="text-3xl font-black text-gradient-gold">{s.num}</div>
                <div className="text-gray-500 text-sm mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 animate-bounce">
        <div className="w-6 h-10 rounded-full border-2 border-white/20 flex items-start justify-center pt-1.5">
          <div className="w-1 h-2.5 bg-white/50 rounded-full animate-pulse" />
        </div>
      </div>
    </section>
  );
};

// ─── Services ─────────────────────────────────────
const ServicesSection: React.FC = () => {
  const services = [
    {
      icon: '🚿',
      title: 'Rửa xe & Hút bụi',
      desc: 'Quy trình rửa xe không trầy, sử dụng hóa chất cao cấp an toàn với sơn xe.',
      tag: 'Phổ biến',
      color: 'from-sky-500/20 to-blue-600/10',
      border: 'group-hover:border-sky-500/40',
    },
    {
      icon: '💎',
      title: 'Phủ Ceramic',
      desc: 'Bảo vệ sơn xe vĩnh cửu. Chống xước, chống tia UV, chống bẩn vượt trội.',
      tag: 'Hot',
      color: 'from-violet-500/20 to-purple-600/10',
      border: 'group-hover:border-violet-500/40',
    },
    {
      icon: '🔧',
      title: 'Bảo dưỡng định kỳ',
      desc: 'Kiểm tra toàn diện 50+ hạng mục. Thay dầu, lọc, phanh, hộp số...',
      tag: 'Cần thiết',
      color: 'from-green-500/20 to-emerald-600/10',
      border: 'group-hover:border-green-500/40',
    },
    {
      icon: '🪟',
      title: 'Nội thất & Da',
      desc: 'Làm sạch, phục hồi da ghế. Khử mùi, diệt khuẩn, làm mới trần xe.',
      tag: '',
      color: 'from-amber-500/20 to-yellow-600/10',
      border: 'group-hover:border-amber-500/40',
    },
    {
      icon: '⚙️',
      title: 'Vệ sinh khoang máy',
      desc: 'Làm sạch sâu khoang động cơ, phát hiện sớm rò rỉ dầu mỡ, bụi bẩn.',
      tag: '',
      color: 'from-orange-500/20 to-red-600/10',
      border: 'group-hover:border-orange-500/40',
    },
    {
      icon: '🔌',
      title: 'Điện & Điện tử',
      desc: 'Chẩn đoán lỗi OBD, sửa hệ thống điện, cảm biến, ECU toàn diện.',
      tag: '',
      color: 'from-cyan-500/20 to-teal-600/10',
      border: 'group-hover:border-cyan-500/40',
    },
  ];

  return (
    <section id="services" className="py-24 px-6 lg:px-10">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <span className="text-cyan-400 text-sm font-bold uppercase tracking-widest">Dịch vụ</span>
          <h2 className="text-4xl md:text-5xl font-black text-white mt-3 mb-4" style={{ letterSpacing: '-0.03em' }}>
            Đầy đủ dịch vụ<br />
            <span className="text-gradient">chăm sóc xe</span>
          </h2>
          <p className="text-gray-500 max-w-xl mx-auto">
            Từ vệ sinh cơ bản đến bảo dưỡng chuyên sâu — tất cả dưới một mái nhà với quy trình chuẩn.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {services.map((s, i) => (
            <div
              key={i}
              className={`group relative glass rounded-2xl p-6 border border-white/8 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${s.border} cursor-pointer`}
            >
              {/* Glow bg */}
              <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${s.color} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />

              <div className="relative z-10">
                <div className="flex items-start justify-between mb-4">
                  <span className="text-3xl">{s.icon}</span>
                  {s.tag && (
                    <span className="text-xs font-bold bg-orange-500/20 text-orange-400 border border-orange-500/30 px-2 py-0.5 rounded-full">
                      {s.tag}
                    </span>
                  )}
                </div>
                <h3 className="text-white font-bold text-lg mb-2">{s.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{s.desc}</p>
                  <div className="mt-4 flex items-center gap-1 text-cyan-400 text-sm font-semibold opacity-0 group-hover:opacity-100 transition-opacity">
                  Đặt lịch dịch vụ này <span>→</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// ─── Why Us ───────────────────────────────────────
const WhyUs: React.FC = () => (
  <section id="about" className="py-20 px-6 lg:px-10 border-y border-white/5">
    <div className="max-w-7xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        {/* Text */}
        <div>
          <span className="text-cyan-400 text-sm font-bold uppercase tracking-widest">Tại sao chọn chúng tôi</span>
          <h2 className="text-4xl md:text-5xl font-black text-white mt-3 mb-6" style={{ letterSpacing: '-0.03em' }}>
            Chất lượng<br />
            <span className="text-gradient">không thỏa hiệp</span>
          </h2>
          <p className="text-gray-400 leading-relaxed mb-8">
            Với hơn 8 năm kinh nghiệm, chúng tôi cam kết mang đến trải nghiệm chăm sóc xe tốt nhất — từ khâu tiếp nhận đến khi bàn giao xe hoàn hảo.
          </p>
          <div className="space-y-4">
            {[
              { icon: '🏅', title: 'Kỹ thuật viên được chứng nhận', desc: 'Đội ngũ đào tạo bài bản, có chứng nhận chuyên môn quốc tế.' },
              { icon: '🧪', title: 'Hóa chất & thiết bị cao cấp', desc: 'Chỉ sử dụng sản phẩm chính hãng, an toàn tuyệt đối với xe.' },
              { icon: '⏰', label: '0', title: 'Đúng hẹn, đúng cam kết', desc: 'Hoàn trả xe đúng giờ, thông báo tiến độ qua điện thoại.' },
              { icon: '🛡️', title: 'Bảo hành dịch vụ', desc: 'Cam kết bảo hành tất cả hạng mục, hoàn tiền nếu không hài lòng.' },
            ].map((item, i) => (
              <div key={i} className="flex gap-4 glass rounded-xl p-4">
                <span className="text-2xl shrink-0">{item.icon}</span>
                <div>
                  <div className="text-white font-semibold text-sm">{item.title}</div>
                  <div className="text-gray-500 text-sm mt-0.5">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-2 gap-4">
          {[
            { num: '5,000+', label: 'Xe đã phục vụ', icon: '🚗', color: '#f97316' },
            { num: '8 năm', label: 'Kinh nghiệm', icon: '📅', color: '#a855f7' },
            { num: '12+', label: 'Kỹ thuật viên', icon: '👨‍🔧', color: '#22c55e' },
            { num: '99%', label: 'Hài lòng', icon: '⭐', color: '#fbbf24' },
          ].map((s, i) => (
            <div key={i} className="glass rounded-2xl p-6 text-center border border-white/8 hover:border-white/16 transition-colors">
              <div className="text-3xl mb-2">{s.icon}</div>
              <div className="text-3xl font-black mb-1" style={{ color: s.color }}>{s.num}</div>
              <div className="text-gray-500 text-sm">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  </section>
);

// ─── Booking Form ─────────────────────────────────
const BookingSection: React.FC = () => {
  const [form, setForm] = useState<FormData>({
    ho_ten: '', sdt: '', bien_so: '',
    dich_vu: '', ngay_hen: '', gio_hen: '', ghi_chu: '',
  });
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));

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
      const res = await fetch('http://localhost:8765/api/booking', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (data.success) {
        setStatus('success');
        setForm({ ho_ten: '', sdt: '', bien_so: '', dich_vu: '', ngay_hen: '', gio_hen: '', ghi_chu: '' });
      } else {
        setErrorMsg(data.error || 'Đã có lỗi xảy ra.');
        setStatus('error');
      }
    } catch {
      setErrorMsg('Không kết nối được tới máy chủ. Kiểm tra kết nối mạng.');
      setStatus('error');
    }
  };

  const inputCls = 'w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-cyan-500/60 focus:bg-white/8 transition-all duration-200 text-sm';
  const labelCls = 'block text-gray-500 text-xs font-semibold mb-2 uppercase tracking-wider';

  return (
    <section id="booking" className="py-24 px-6 lg:px-10">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-12 items-start">
          {/* Left — info */}
          <div className="lg:col-span-2">
            <span className="text-cyan-400 text-sm font-bold uppercase tracking-widest">Đặt lịch trực tuyến</span>
            <h2 className="text-4xl md:text-5xl font-black text-white mt-3 mb-6" style={{ letterSpacing: '-0.03em' }}>
              Đặt lịch<br />
              <span className="text-gradient">trong 60 giây</span>
            </h2>
            <p className="text-gray-400 leading-relaxed mb-8">
              Điền form bên cạnh — chúng tôi sẽ liên hệ xác nhận trong vòng <strong className="text-white">30 phút</strong>. Không cần gọi điện, không cần chờ đợi.
            </p>

            <div className="space-y-4">
              {[
                { icon: '📍', title: 'Địa chỉ', desc: '123 Đường Lê Lợi, Quận 1, TP.HCM' },
                { icon: '⏰', title: 'Giờ mở cửa', desc: 'Thứ 2 – CN: 07:00 – 20:00' },
                { icon: '📞', title: 'Hotline', desc: '1900 xxxx (miễn phí)' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-4">
                  <div className="w-10 h-10 glass rounded-xl flex items-center justify-center text-lg shrink-0">
                    {item.icon}
                  </div>
                  <div>
                    <div className="text-gray-500 text-xs">{item.title}</div>
                    <div className="text-white text-sm font-medium">{item.desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Trust badges */}
            <div className="flex flex-wrap gap-3 mt-8">
              {['✓ Xác nhận nhanh', '✓ Không phát sinh phí', '✓ Bảo hành dịch vụ'].map(b => (
                <span key={b} className="text-xs text-cyan-400 bg-cyan-400/10 border border-cyan-400/20 px-3 py-1.5 rounded-full font-medium">
                  {b}
                </span>
              ))}
            </div>
          </div>

          {/* Right — form */}
          <div className="lg:col-span-3">
            <div className="glass rounded-3xl p-8 border border-white/8">
              {status === 'success' ? (
                <div className="text-center py-12">
                  <div className="w-20 h-20 bg-green-500/10 border border-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6 text-4xl">
                    ✅
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-3">Đặt lịch thành công!</h3>
                  <p className="text-gray-400 mb-8 max-w-sm mx-auto">
                    Chúng tôi đã nhận được yêu cầu và sẽ gọi xác nhận trong vòng 30 phút.
                  </p>
                  <button
                    onClick={() => setStatus('idle')}
                    className="bg-cyan-500 text-white px-8 py-3 rounded-full font-semibold hover:bg-cyan-600 transition-all"
                  >
                    Đặt lịch khác
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className={labelCls}>Họ và tên *</label>
                      <input type="text" name="ho_ten" value={form.ho_ten} onChange={handleChange} placeholder="Nguyễn Văn A" className={inputCls} required />
                    </div>
                    <div>
                      <label className={labelCls}>Số điện thoại *</label>
                      <input type="tel" name="sdt" value={form.sdt} onChange={handleChange} placeholder="0901 234 567" className={inputCls} required />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className={labelCls}>Biển số xe</label>
                      <input type="text" name="bien_so" value={form.bien_so} onChange={handleChange} placeholder="51A-12345" className={inputCls} />
                    </div>
                    <div>
                      <label className={labelCls}>Dịch vụ</label>
                      <select name="dich_vu" value={form.dich_vu} onChange={handleChange} className={`${inputCls} cursor-pointer`}>
                        <option value="" className="bg-[#111]">Chọn dịch vụ...</option>
                        {SERVICES.map(s => (
                          <option key={s.id} value={s.label} className="bg-[#111]">{s.icon} {s.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className={labelCls}>Ngày hẹn</label>
                      <input type="date" name="ngay_hen" value={form.ngay_hen} onChange={handleChange} className={`${inputCls} [color-scheme:dark]`} />
                    </div>
                    <div>
                      <label className={labelCls}>Giờ hẹn</label>
                      <input type="time" name="gio_hen" value={form.gio_hen} onChange={handleChange} min="07:00" max="20:00" className={`${inputCls} [color-scheme:dark]`} />
                    </div>
                  </div>

                  <div>
                    <label className={labelCls}>Yêu cầu / ghi chú</label>
                    <textarea name="ghi_chu" value={form.ghi_chu} onChange={handleChange} placeholder="Xe bị trầy nhẹ phần đầu, cần kiểm tra thêm..." rows={3} className={`${inputCls} resize-none`} />
                  </div>

                  {status === 'error' && errorMsg && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl px-4 py-3">
                      ⚠️ {errorMsg}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full bg-cyan-500 text-white font-bold py-4 rounded-xl text-sm hover:bg-cyan-600 transition-all duration-200 shadow-xl shadow-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:scale-100"
                  >
                    {status === 'loading' ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <circle cx="12" cy="12" r="10" strokeWidth="4" className="opacity-25" />
                          <path d="M4 12a8 8 0 018-8" strokeWidth="4" />
                        </svg>
                        Đang gửi...
                      </span>
                    ) : '🗓️  Xác nhận đặt lịch'}
                  </button>

                  <p className="text-center text-gray-600 text-xs">
                    Thông tin của bạn được bảo mật hoàn toàn. Chúng tôi sẽ chỉ liên hệ để xác nhận lịch hẹn.
                  </p>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

// ─── Footer ───────────────────────────────────────
const Footer: React.FC = () => (
  <footer className="border-t border-white/5 py-12 px-6 lg:px-10">
    <div className="max-w-7xl mx-auto">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
        <div>
            <div className="flex items-center gap-3 mb-4">
              <img src="/logo.png" alt="Car Care" className="h-12 w-auto object-contain" />
            </div>
          <p className="text-gray-600 text-sm leading-relaxed">Trung tâm chăm sóc xe ô tô hàng đầu với 8 năm kinh nghiệm và hơn 5.000 khách hàng tin tưởng.</p>
        </div>
        <div>
          <div className="text-white font-semibold mb-4">Dịch vụ</div>
          <div className="space-y-2 text-sm text-gray-600">
            {['Rửa xe & Hút bụi', 'Phủ Ceramic', 'Bảo dưỡng định kỳ', 'Vệ sinh nội thất', 'Sửa chữa điện tử'].map(s => (
              <div key={s} className="hover:text-gray-400 cursor-pointer transition-colors">{s}</div>
            ))}
          </div>
        </div>
        <div>
          <div className="text-white font-semibold mb-4">Liên hệ</div>
          <div className="space-y-3 text-sm text-gray-600">
            <div>📍 123 Đường Lê Lợi, Q.1, TP.HCM</div>
            <div>📞 1900 xxxx</div>
            <div>✉️ contact@autocare.vn</div>
            <div>⏰ 07:00 – 20:00 | Thứ 2 – CN</div>
          </div>
        </div>
      </div>
      <div className="border-t border-white/5 pt-6 flex flex-col md:flex-row items-center justify-between gap-3">
        <p className="text-gray-700 text-xs">© 2026 AutoCare Pro Center. Hệ thống quản lý dịch vụ chăm sóc xe ô tô.</p>
        <p className="text-gray-700 text-xs">Thiết kế bởi đội ngũ kỹ thuật AutoCare</p>
      </div>
    </div>
  </footer>
);

// ─── Main App ─────────────────────────────────────
export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] font-sans">
      <Navbar />
      <Hero />
      <ServicesSection />
      <WhyUs />
      <BookingSection />
      <Footer />
    </div>
  );
}
