import React, { useEffect, useRef } from "react"
import { ChevronDown, Check } from "lucide-react"
import { Button } from "./components/ui/button"
import { BookingForm } from "./components/BookingForm"

function Navbar() {
  return (
    <>
      <nav className="w-full py-5 px-8 flex flex-row items-center justify-between">
        <div className="flex items-center">
          <img src="/logo.png" alt="Logo" className="h-[32px] w-auto object-contain" />
        </div>
        <div className="hidden md:flex items-center gap-1">
          <button data-scroll-id="services" className="flex items-center gap-1 px-3 py-2 text-foreground/90 text-base font-medium hover:text-foreground transition-colors">
            Dịch vụ <ChevronDown className="w-4 h-4 opacity-50 pointer-events-none" />
          </button>
          <button data-scroll-id="pricing" className="flex items-center gap-1 px-3 py-2 text-foreground/90 text-base font-medium hover:text-foreground transition-colors">
            Bảng giá
          </button>
          <button data-scroll-id="about" className="flex items-center gap-1 px-3 py-2 text-foreground/90 text-base font-medium hover:text-foreground transition-colors">
            Về chúng tôi
          </button>
          <button data-scroll-id="knowledge" className="flex items-center gap-1 px-3 py-2 text-foreground/90 text-base font-medium hover:text-foreground transition-colors">
            Kiến thức <ChevronDown className="w-4 h-4 opacity-50 pointer-events-none" />
          </button>
        </div>
        <div className="flex items-center">
          <Button variant="heroSecondary" size="sm" className="rounded-full px-4 py-2">
            Đăng nhập
          </Button>
        </div>
      </nav>
      <div className="mt-[3px] w-full h-px bg-gradient-to-r from-transparent via-foreground/20 to-transparent" />
    </>
  )
}

function HeroVideoSection() {
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    let animationFrameId: number

    const updateOpacity = () => {
      const currentTime = video.currentTime
      const duration = video.duration || 0.1
      
      const fadeDuration = 0.5
      let nextOpacity = 1

      if (currentTime < fadeDuration) {
        nextOpacity = currentTime / fadeDuration
      } else if (duration - currentTime < fadeDuration) {
        nextOpacity = (duration - currentTime) / fadeDuration
      }

      nextOpacity = Math.max(0, Math.min(1, nextOpacity))
      video.style.opacity = nextOpacity.toString()

      animationFrameId = requestAnimationFrame(updateOpacity)
    }

    const handleEnded = () => {
      video.style.opacity = "0"
      setTimeout(() => {
        video.currentTime = 0
        video.play().catch(console.error)
      }, 100)
    }

    video.addEventListener("ended", handleEnded)
    video.play().catch(console.error)
    animationFrameId = requestAnimationFrame(updateOpacity)

    return () => {
      video.removeEventListener("ended", handleEnded)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  const handleScroll = () => {
    document.getElementById('booking')?.scrollIntoView({ behavior: 'smooth' })
  }

  const brands = [
    { 
      name: "Mercedes", 
      svg: (
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="3" className="w-8 h-8 text-white/50 group-hover:text-white transition-all duration-500">
          <circle cx="50" cy="50" r="45"/><path d="M50 5 L50 50 L10 75 M50 50 L90 75" />
        </svg>
      )
    },
    { 
      name: "Porsche", 
      svg: (
        <svg viewBox="0 0 100 120" fill="none" stroke="currentColor" strokeWidth="3" className="w-7 h-9 text-white/50 group-hover:text-white transition-all duration-500">
          <path d="M20 20 Q50 0 80 20 L80 80 Q50 120 20 80 Z" />
          <path d="M50 30 L40 50 L60 50 Z M30 80 Q50 100 70 80" strokeWidth="2" />
        </svg>
      )
    },
    { 
      name: "BMW", 
      svg: (
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="3" className="w-8 h-8 text-white/50 group-hover:text-white transition-all duration-500">
          <circle cx="50" cy="50" r="45"/><circle cx="50" cy="50" r="28"/><path d="M50 22 L50 78 M22 50 L78 50" />
        </svg>
      )
    },
    { 
      name: "Audi", 
      svg: (
        <svg viewBox="0 0 100 40" fill="none" stroke="currentColor" strokeWidth="3" className="w-12 h-6 text-white/50 group-hover:text-white transition-all duration-500">
          <circle cx="20" cy="20" r="14"/><circle cx="40" cy="20" r="14"/><circle cx="60" cy="20" r="14"/><circle cx="80" cy="20" r="14"/>
        </svg>
      )
    },
    { 
      name: "Lexus", 
      svg: (
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="3" className="w-8 h-8 text-white/50 group-hover:text-white transition-all duration-500">
          <circle cx="50" cy="50" r="45"/><path d="M60 25 L35 70 Q45 75 75 60" />
        </svg>
      )
    },
    { 
      name: "Volvo", 
      svg: (
        <svg viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="3" className="w-8 h-8 text-white/50 group-hover:text-white transition-all duration-500">
          <circle cx="40" cy="60" r="35"/><path d="M65 35 L90 10 M90 10 L70 10 M90 10 L90 30" />
        </svg>
      )
    }
  ]
  const duplicatedBrands = [...brands, ...brands, ...brands]

  return (
    <section className="relative w-full min-h-[100vh] flex flex-col bg-background overflow-hidden">
      <video 
        ref={videoRef}
        autoPlay 
        muted 
        playsInline 
        className="absolute inset-0 w-full h-full object-cover"
        style={{ opacity: 0 }}
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260308_114720_3dabeb9e-2c39-4907-b747-bc3544e2d5b7.mp4"
      />
      <div className="absolute inset-0 bg-gradient-to-b from-[#030712]/20 via-[#030712]/50 to-background pointer-events-none z-0" />
      
      <div className="relative z-20 w-full">
        <Navbar />
      </div>
      
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 w-full pt-10">
        <div className="mb-4 text-cyan-400 font-semibold tracking-wider text-sm uppercase shadow-sm">Trung tâm AutoCare</div>
        <h1 
          className="text-[80px] md:text-[180px] font-normal leading-[1.02] tracking-[-0.024em] bg-clip-text text-transparent text-center drop-shadow-2xl"
          style={{ 
            fontFamily: "'General Sans', sans-serif",
            backgroundImage: "linear-gradient(223deg, #ffffff 0%, #06b6d4 104.15%)"
          }}
        >
          ProCare
        </h1>
        <p className="text-white text-center text-lg md:text-xl font-light leading-10 max-w-lg mt-6 opacity-90 drop-shadow-lg">
          Biến chiếc xe của bạn trở nên hoàn hảo<br />với dịch vụ chăm sóc cao cấp nhất.
        </p>
        <div className="mt-12 mb-[80px]">
          <Button variant="heroSecondary" onClick={handleScroll} className="px-[32px] py-[28px] text-[17px] shadow-[0_0_30px_rgba(6,182,212,0.3)]">
            Hẹn lịch chăm sóc
          </Button>
        </div>
      </div>
      
      <div className="relative z-10 w-full max-w-5xl mx-auto flex flex-col md:flex-row items-center gap-8 md:gap-16 pb-12 px-4">
        <div className="text-white/60 text-sm whitespace-nowrap shrink-0 text-center md:text-left drop-shadow-md">
          Được tin tưởng bởi các chủ xe <br className="hidden md:block" />
          đến từ thương hiệu hàng đầu
        </div>
        
        <div className="flex-1 overflow-hidden relative mask-image-linear">
          <div className="absolute inset-y-0 left-0 w-12 bg-gradient-to-r from-background to-transparent z-10" />
          <div className="absolute inset-y-0 right-0 w-12 bg-gradient-to-l from-background to-transparent z-10" />
          
          <div className="flex animate-marquee whitespace-nowrap items-center">
            {duplicatedBrands.map((brand, i) => (
              <div key={i} className="flex items-center gap-4 mx-8 shrink-0 group cursor-pointer hover:scale-105 transition-transform">
                <div className="drop-shadow-[0_0_15px_rgba(255,255,255,0.1)] group-hover:drop-shadow-[0_0_20px_rgba(255,255,255,0.4)] transition-all">
                  {brand.svg}
                </div>
                <span className="text-xl font-medium text-white/50 group-hover:text-white transition-colors tracking-widest uppercase text-sm drop-shadow-lg">{brand.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function ServicesSection() {
  const services = [
    { title: "Rửa xe siêu tốc", desc: "Sạch bong rạng ngời chỉ trong 30 phút với quy trình chuẩn Mỹ." },
    { title: "Phủ Ceramic 9H", desc: "Bảo vệ sơn tuyệt đối, hiệu ứng lá sen kháng nước đỉnh cao." },
    { title: "Vệ sinh nội thất", desc: "Diệt khuẩn bằng hơi nước nóng, làm mới da và nhựa an toàn." },
    { title: "Đánh bóng màng sơn", desc: "Loại bỏ hoàn toàn vết xước xoáy, trả lại vẻ đẹp như mới." }
  ]

  return (
    <section id="services" className="w-full py-24 px-6 md:px-12 bg-background relative z-10">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-4xl font-normal mb-16 text-center text-foreground">
          Dịch vụ <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">nổi bật</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {services.map((s, i) => (
            <div key={i} className="liquid-glass border border-white/5 rounded-2xl p-8 hover:border-cyan-500/50 transition-colors group cursor-pointer">
              <div className="w-12 h-12 rounded-full bg-cyan-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <div className="w-4 h-4 bg-cyan-400 rounded-full shadow-[0_0_10px_rgba(6,182,212,0.8)]" />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-foreground">{s.title}</h3>
              <p className="text-foreground/60 leading-relaxed text-sm">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function PricingSection() {
  return (
    <section id="pricing" className="w-full py-24 px-6 md:px-12 bg-background relative z-10">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-4xl font-normal mb-16 text-center text-foreground">
          Bảng giá <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">dịch vụ</span>
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Basic */}
          <div className="liquid-glass border border-white/5 rounded-3xl p-8 flex flex-col mt-6 md:mt-0 hover:border-white/20 transition-colors">
            <h3 className="text-xl font-medium text-foreground/80 mb-2">Gói Cơ Bản</h3>
            <div className="text-5xl font-bold text-foreground mb-6 tracking-tight">250K</div>
            <div className="w-full h-px bg-white/10 mb-6" />
            <ul className="space-y-4 mb-8 flex-1 text-sm text-foreground/80">
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Rửa xe chi tiết không chạm</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Hút bụi nội thất</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Xịt gầm xe</span></li>
              <li className="flex items-start gap-3 opacity-40"><span className="w-5 h-5 shrink-0 flex items-center justify-center">-</span> <span>Tẩy ố kính, nhựa đường</span></li>
              <li className="flex items-start gap-3 opacity-40"><span className="w-5 h-5 shrink-0 flex items-center justify-center">-</span> <span>Phủ wax bảo vệ sơn</span></li>
            </ul>
            <button className="w-full py-4 rounded-xl bg-white/5 text-white font-semibold hover:bg-white/10 transition-colors border border-white/10">Chọn Cấp Cơ Bản</button>
          </div>
          
          {/* Pro */}
          <div className="liquid-glass border border-cyan-500/50 rounded-3xl p-8 flex flex-col relative transform md:-translate-y-4 shadow-[0_0_40px_rgba(6,182,212,0.15)] mt-6 md:mt-0">
            <div className="flex justify-between items-start mb-2 mt-1">
              <h3 className="text-xl font-medium text-cyan-400">Gói Cao Cấp</h3>
              <div className="bg-cyan-500 text-black text-[10px] font-bold px-3 py-1 rounded-full tracking-widest shadow-[0_0_20px_rgba(6,182,212,0.5)]">
                PHỔ BIẾN
              </div>
            </div>
            <div className="text-5xl font-bold text-foreground mb-6 tracking-tight">850K</div>
            <div className="w-full h-px bg-cyan-500/30 mb-6" />
            <ul className="space-y-4 mb-8 flex-1 text-sm text-foreground/90">
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Toàn bộ Gói Cơ Bản</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Vệ sinh nội thất sâu</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Tẩy ố kính, nhựa đường</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-cyan-500 shrink-0" /> <span>Phủ wax bảo vệ sơn</span></li>
              <li className="flex items-start gap-3 opacity-40"><span className="w-5 h-5 shrink-0 flex items-center justify-center">-</span> <span>Phủ Ceramic 9H siêu bóng</span></li>
            </ul>
            <button className="w-full py-4 rounded-xl bg-cyan-500 text-black font-extrabold hover:bg-cyan-400 hover:shadow-[0_0_20px_rgba(6,182,212,0.4)] transition-all">Chọn Gói Cao Cấp</button>
          </div>

          {/* VIP */}
          <div className="liquid-glass border border-white/5 rounded-3xl p-8 flex flex-col mt-6 md:mt-0 hover:border-white/20 transition-colors">
            <h3 className="text-xl font-medium text-purple-400 mb-2">Gói VIP Ceramic</h3>
            <div className="text-5xl font-bold text-foreground mb-6 tracking-tight">4.5M+</div>
            <div className="w-full h-px bg-purple-500/30 mb-6" />
            <ul className="space-y-4 mb-8 flex-1 text-sm text-foreground/80">
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-purple-400 shrink-0" /> <span>Rửa xe siêu chi tiết</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-purple-400 shrink-0" /> <span>Đánh bóng 3 bước xóa xước</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-purple-400 shrink-0" /> <span>Vệ sinh khoang máy</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-purple-400 shrink-0" /> <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-500 font-bold">Phủ Ceramic 9H chống trầy</span></li>
              <li className="flex items-start gap-3"><Check className="w-5 h-5 text-purple-400 shrink-0" /> <span>Bảo hành độ bóng 2 năm</span></li>
            </ul>
            <button className="w-full py-4 rounded-xl bg-purple-600/20 text-purple-300 font-semibold hover:bg-purple-600/40 border border-purple-500/30 transition-colors">Liên Hệ Tư Vấn</button>
          </div>
        </div>
      </div>
    </section>
  )
}

function AboutUsSection() {
  return (
    <section id="about" className="w-full py-32 px-6 md:px-12 bg-background relative z-10 overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-cyan-600/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center gap-16 relative z-10">
        <div className="flex-1">
          <h2 className="text-4xl md:text-5xl font-normal mb-6 text-foreground">
            Về <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">chúng tôi</span>
          </h2>
          <p className="text-foreground/70 text-lg leading-relaxed mb-8">
            Ra đời từ sự đam mê cái đẹp của xe hơi, AutoCare hướng tới mục tiêu cung cấp giải pháp chăm sóc toàn diện nhất. 
            Chúng tôi sử dụng 100% dung dịch đạt chuẩn an toàn môi trường và máy móc chuyển giao từ Đức.
          </p>
          <div className="flex gap-8">
            <div>
              <div className="text-3xl font-bold text-cyan-400 mb-2">5+</div>
              <div className="text-sm text-foreground/60 uppercase tracking-wider">Năm kinh nghiệm</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-cyan-400 mb-2">10k+</div>
              <div className="text-sm text-foreground/60 uppercase tracking-wider">Khách hài lòng</div>
            </div>
          </div>
        </div>
        <div className="flex-1 w-full relative">
          <div className="aspect-video rounded-3xl overflow-hidden border border-white/10 liquid-glass flex items-center justify-center p-2 relative shadow-[0_0_50px_rgba(6,182,212,0.2)]">
             <img src="/garage.png" alt="Auto Care Garage" className="w-full h-full object-cover rounded-2xl" />
          </div>
        </div>
      </div>
    </section>
  )
}

function KnowledgeSection() {
  const blogs = [
    { img: "/blog.png", title: "Cách chăm sóc sơn xe mùa mưa bão", desc: "Những lưu ý quan trọng để tránh bị ố kính và bạc màu sơn do sương muối và axit." },
    { img: "/blog2.png", title: "Hiểu đúng về Phủ Ceramic", desc: "Ceramic có thực sự chống xước 100% như quảng cáo? Chuyên gia giải đáp." },
    { img: "/blog3.png", title: "Cách vệ sinh nội thất da cao cấp", desc: "Sử dụng đúng dung dịch để giữ da ghế luôn mềm mại và không bị nứt nẻ." },
  ]

  return (
    <section id="knowledge" className="w-full py-24 px-6 md:px-12 bg-background relative z-10">
      <div className="max-w-5xl mx-auto text-center">
        <h2 className="text-4xl font-normal mb-8 text-foreground">
          Góc <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">kiến thức</span>
        </h2>
        <p className="text-foreground/60 max-w-2xl mx-auto mb-16">
          Bí quyết giúp giữ gìn lớp sơn xe luôn sáng bóng, nội thất luôn thơm tho như lúc mới mua.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          {blogs.map((b, item) => (
             <div key={item} className="liquid-glass border border-white/5 rounded-2xl overflow-hidden group cursor-pointer hover:border-cyan-500/50 transition-colors shadow-lg">
               <div className="h-48 bg-foreground/5 relative overflow-hidden">
                 <img src={b.img} alt="Car Care" className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                 <div className="absolute inset-0 bg-gradient-to-t from-[#0b1120] to-transparent z-10" />
               </div>
               <div className="p-6">
                 <div className="text-xs text-cyan-400 font-semibold uppercase tracking-wider mb-3">Kinh nghiệm</div>
                 <h3 className="text-lg font-medium text-foreground mb-2 group-hover:text-cyan-400 transition-colors">{b.title}</h3>
                 <p className="text-sm text-foreground/60">{b.desc}</p>
               </div>
             </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function App() {
  // Thay thế handleScroll sang các sections tự động
  useEffect(() => {
    const handleNavClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.dataset.scrollId) {
        document.getElementById(target.dataset.scrollId)?.scrollIntoView({ behavior: 'smooth' })
      }
    }
    document.addEventListener('click', handleNavClick)
    return () => document.removeEventListener('click', handleNavClick)
  }, [])

  return (
    <main className="min-h-screen font-sans bg-background text-foreground antialiased selection:bg-primary/30">
      <HeroVideoSection />
      <ServicesSection />
      <PricingSection />
      <AboutUsSection />
      <KnowledgeSection />
      <BookingForm />
    </main>
  )
}

export default App
