import React from 'react';
import { useNavigate } from 'react-router-dom';
import Header from './Header.jsx';
import './CSS/Global.css';
import './CSS/HeroSection.css';
import './CSS/VideoSection.css';
import './CSS/StatisticsSection.css';
import './CSS/DiscoverySection.css';
import './CSS/ContactSection.css';
import './CSS/CTASection.css';
import './CSS/Footer.css';
import './CSS/LottieBot.css';
import './CSS/ScrollReveal.css';
import LottieBot from './components/LottieBot.jsx';

// Animated Counter Component
const AnimatedCounter = ({ end, suffix = "", duration = 2000 }) => {
  const [count, setCount] = React.useState(0);
  const ref = React.useRef(null);
  const started = React.useRef(false);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          let startTime = null;
          const animate = (currentTime) => {
            if (!startTime) startTime = currentTime;
            const progress = Math.min((currentTime - startTime) / duration, 1);
            const easeOutExpo = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
            setCount(Math.floor(easeOutExpo * end));
            if (progress < 1) requestAnimationFrame(animate);
            else setCount(end);
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, duration]);

  return <span ref={ref}>{count}{suffix}</span>;
};

const TrangGioiThieu = () => {
  const navigate = useNavigate();
  const [scrolled, setScrolled] = React.useState(false);
  const [scrollProgress, setScrollProgress] = React.useState(0);

  const scrollToContact = () => {
    document.querySelector('.contact-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    const target = window.history.state?.usr?.scrollTo;
    if (target) {
      setTimeout(() => {
        document.getElementById(target)?.scrollIntoView({ behavior: 'smooth' });
      }, 300);
    }
  }, []);

  React.useEffect(() => {
    const onScroll = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setScrolled(scrollTop > 50);
      setScrollProgress(docHeight > 0 ? (scrollTop / docHeight) * 100 : 0);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('is-revealed');
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    );
    const els = document.querySelectorAll('.reveal-init');
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const playVideo = () => {
    const video = document.getElementById('campusVideo');
    if (video && video.paused) {
      video.play().catch(() => {
        window.open('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '_blank');
      });
    }
  };

  const goToChat = () => navigate('/chat');

  return (
    <div className="page-wrapper">
      <div className="scroll-progress-container">
        <div className="scroll-progress-bar" style={{ width: `${scrollProgress}%` }} />
      </div>

      <Header scrolled={scrolled} />
      <LottieBot />

      <section className="hero-section aurora-bg-mesh" aria-labelledby="hero-title">
        <div className="aurora-blob aurora-blob-1" />
        <div className="aurora-blob aurora-blob-2" />
        <div className="cyber-grid-overlay" />
        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          <div className="futuristic-badge reveal-init reveal-up">
            <span className="futuristic-badge-dot" /> <span>CHATBOT UTH XIN CHÀO! </span>
          </div>
          <img
            src="/images/hero-illustration.png"
            alt="Minh họa AI Assistant của UTH"
            className="hero-illustration reveal-init reveal-scale"
          />
          <div className="hero-content">
            <h1 id="hero-title" className="hero-title reveal-init reveal-up delay-100">
              <span className="title-dark">Trợ lý</span>
              <span className="title-primary">tuyển sinh</span>
            </h1>

            <p className="hero-subtitle reveal-init reveal-up delay-200">
              Trường Đại học Giao thông vận tải TP. Hồ Chí Minh
            </p>

            <div className="hero-actions reveal-init reveal-up delay-300">
              <button className="btn btn-primary btn-shimmer" onClick={goToChat}>
                Trò chuyện với trợ lý
              </button>

              <p className="hero-actions-hint">
                Tư vấn 24/7, đa dạng thông tin
              </p>
            </div>

            <div className="welcome-container reveal-init reveal-up delay-400">
              <h2 className="welcome-title">WELCOME TO UTH</h2>
            </div>
          </div>
        </div>
      </section>

      <div className="section-divider"><div className="section-divider-line" /></div>

      <section id="video-section" className="video-section aurora-bg-mesh" aria-labelledby="video-title">
        <div className="aurora-blob aurora-blob-2" />
        <div className="video-container video-theater-glow reveal-init reveal-scale" style={{ position: 'relative', zIndex: 1 }}>
          <iframe
            className="video-poster"
            src="https://www.youtube.com/embed/g-g5l-4iaYU"
            title="UTH Campus"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          ></iframe>
        </div>
      </section>

      <div className="section-divider"><div className="section-divider-line" /></div>

      <section className="statistics-section aurora-bg-mesh" aria-labelledby="stats-title">
        <div className="aurora-blob aurora-blob-1" />
        <div className="container" style={{ position: 'relative', zIndex: 1 }}>
          <h2 id="stats-title" className="section-title reveal-init reveal-up">
            Số liệu <span>ấn tượng</span>
          </h2>
          <div className="stats-grid">
            <article className="stat-card glass-cyber-card reveal-init reveal-up delay-100">
              <span className="stat-watermark">01</span>
              <div className="stat-number stat-number-animated"><AnimatedCounter end={35} suffix="+" /></div>
              <div className="stat-title">Năm hình thành & Phát triển</div>
              <p className="stat-description">Hành trình hơn ba thập kỷ đào tạo nhân lực chất lượng cao cho ngành giao thông vận tải</p>
            </article>
            <article className="stat-card glass-cyber-card reveal-init reveal-up delay-200">
              <span className="stat-watermark">02</span>
              <div className="stat-number stat-number-animated"><AnimatedCounter end={50} suffix="+" /></div>
              <div className="stat-title">Câu lạc bộ sinh viên</div>
              <p className="stat-description">Môi trường năng động giúp sinh viên phát triển kỹ năng mềm, nghệ thuật và thể thao</p>
            </article>
            <article className="stat-card glass-cyber-card reveal-init reveal-up delay-300">
              <span className="stat-watermark">03</span>
              <div className="stat-number stat-number-animated"><AnimatedCounter end={6} /></div>
              <div className="stat-title">Cơ sở đào tạo chính quy hiện đại</div>
              <p className="stat-description">Hệ thống cơ sở trải dài từ TP.HCM, Vũng Tàu đến Đồng Nai với trang thiết bị tiên tiến</p>
            </article>
          </div>
        </div>
      </section>

      <div className="section-divider"><div className="section-divider-line" /></div>

      <section className="discovery-section" aria-labelledby="discovery-title">
        <div className="container">
          <h2 id="discovery-title" className="section-title reveal-init reveal-up">
            Khám phá <span>UTH</span>
          </h2>
          <div className="discovery-grid">
            <a href="#contact" className="discovery-card-link reveal-init reveal-up delay-100">
              <article className="discovery-card glass-cyber-card">
                <img className="discovery-image" src="/icons/discovery-contact.png" alt="Thông tin liên hệ UTH" />
                <div className="discovery-overlay">
                  <div className="discovery-content">
                    <i className="fa-solid fa-phone discovery-icon" />
                    <h3 className="discovery-title">Thông tin liên hệ</h3>
                  </div>
                </div>
              </article>
            </a>
            <a href="https://uth.edu.vn/" target="_blank" rel="noopener noreferrer" className="discovery-card-link reveal-init reveal-up delay-200">
              <article className="discovery-card glass-cyber-card">
                <img className="discovery-image" src="/icons/discovery-web.png" alt="Website UTH" />
                <div className="discovery-overlay">
                  <div className="discovery-content">
                    <i className="fa-solid fa-globe discovery-icon" />
                    <h3 className="discovery-title">Website UTH</h3>
                  </div>
                </div>
              </article>
            </a>
            <a href="#video-section" className="discovery-card-link reveal-init reveal-up delay-300">
              <article className="discovery-card glass-cyber-card">
                <img className="discovery-image" src="/icons/discovery-video.png" alt="Video giới thiệu UTH" />
                <div className="discovery-overlay">
                  <div className="discovery-content">
                    <i className="fa-solid fa-video discovery-icon" />
                    <h3 className="discovery-title">Video giới thiệu</h3>
                  </div>
                </div>
              </article>
            </a>
          </div>
        </div>
      </section>

      <section id="contact" className="contact-section" aria-labelledby="contact-title">
        <div className="container">
          <h2 id="contact-title" className="section-title">Liên hệ <span>UTH</span></h2>
          <div className="contact-grid">
            <div className="contact-map-card">
              <iframe
                src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3919.088330808492!2d106.71425487594014!3d10.80454658934592!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3175293dceb22197%3A0x755bb0f39a48d4a6!2zVHLGsOG7nW5nIMSQ4bqhaSBI4buNYyBHaWFvIFRow7RuZyBW4bqtbiBU4bqjaSBUaMOgbmggUGjhu5EgSOG7kyBDaMOtIE1pbmggLSBDxqEgc-G7nyAx!5e0!3m2!1svi!2s!4v1787121747330!5m2!1svi!2s"
                width="100%"
                height="450"
                style={{ border: 0 }}
                allowFullScreen
                loading="lazy"
                referrerPolicy="strict-origin-when-cross-origin"
                title="Bản đồ cơ sở UTH"
              ></iframe>
            </div>
            <div className="contact-details-card">
              <div className="contact-info-grid">
                <div className="contact-info-item">
                  <div className="contact-icon-wrapper">
                    <i className="fa-solid fa-location-dot" />
                  </div>
                  <div className="contact-info-content">
                    <span className="contact-info-label">Cơ sở đào tạo</span>
                    <div className="contact-info-list">
                      <div style={{ fontWeight: '700', marginBottom: '8px' }}>HỆ CHÍNH QUY</div>
                      <div className="contact-info-value"><span className="contact-info-key">Cơ sở 1 (trụ sở chính):</span><span className="contact-info-text">Số 2 Võ Oanh, phường Thạnh Mỹ Tây, Q. Bình Thạnh, TP.HCM</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">Cơ sở 2:</span><span className="contact-info-text">Số 10 đường số 12, phường An Khánh, TP. Thủ Đức, TP.HCM</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">Cơ sở 3:</span><span className="contact-info-text">Số 70 Tô Ký, phường Tân Chánh Hiệp, Q.12, TP.HCM</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">Cơ sở 4:</span><span className="contact-info-text">Số 17A đường 3 Tháng 2, phường 11, TP. Vũng Tàu, tỉnh Bà Rịa – Vũng Tàu</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">Cơ sở 5:</span><span className="contact-info-text">Xã Bình An, tỉnh Đồng Nai</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">Cơ sở 6 (mới 2026):</span><span className="contact-info-text">Số 33 Đào Trí, phường Phú Thuận, TP.HCM</span></div>
                      <div style={{ fontWeight: '700', marginTop: '16px', marginBottom: '8px' }}>HỆ ĐÀO TẠO THƯỜNG XUYÊN</div>
                      <div className="contact-info-value"><span className="contact-info-key">VP Bình Tân:</span><span className="contact-info-text">Số 234–236 Đường số 1, phường An Lạc, Q. Bình Tân, TP.HCM</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">VP Bình Thạnh:</span><span className="contact-info-text">Số 37/5 Ngô Tất Tố, phường Thạnh Mỹ Tây, TP.HCM</span></div>
                      <div className="contact-info-value"><span className="contact-info-key">VP Gò Vấp:</span><span className="contact-info-text">Số 8A Nguyễn Thái Sơn, phường 3, Q. Gò Vấp, TP.HCM</span></div>
                    </div>
                  </div>
                </div>
                <div className="contact-info-item">
                  <div className="contact-icon-wrapper">
                    <i className="fa-regular fa-envelope" />
                  </div>
                  <div className="contact-info-content">
                    <span className="contact-info-label">Tuyển sinh</span>
                    <div className="contact-info-list">
                      <div className="contact-info-value"><span className="contact-info-text">Hotline: 028 3899 6199</span></div>
                      <div className="contact-info-value"><span className="contact-info-text">Email: tuyensinh@uth.edu.vn</span></div>
                    </div>
                  </div>
                </div>
                <div className="contact-info-item">
                  <div className="contact-icon-wrapper">
                    <i className="fa-solid fa-globe" />
                  </div>
                  <div className="contact-info-content">
                    <span className="contact-info-label">Website</span>
                    <div className="contact-info-list">
                      <a href="https://uth.edu.vn/" target="_blank" rel="noopener noreferrer" className="contact-info-link">https://uth.edu.vn/</a>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="cta-section" aria-labelledby="cta-title">
        <div className="cta-banner">
          <div className="cta-content">
            <div className="cta-left">
              <button className="cta-icon-box" aria-label="Trò chuyện với trợ lý">
                <i className="fa-regular fa-comment" />
              </button>
              <div className="cta-text">
                <h2 id="cta-title" className="cta-title">
                  Luôn sẵn sàng hỗ trợ bạn <br />
                  mọi lúc
                </h2>
              </div>
            </div>
            <button className="cta-start-btn" onClick={goToChat}>Bắt đầu</button>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-container">
          <div className="footer-main">
            <div className="footer-brand">
              <img src="/images/logo-full.png" alt="UTH Logo" className="footer-logo" />
              <p className="footer-tagline">Trường Đại học Giao thông vận tải TP. Hồ Chí Minh</p>
              <div id="text-36" className="widget single-sidebar widget_text">
                <h2 className="widget-title">LIÊN HỆ</h2>
                <div className="textwidget">
                  <div className="wpcf7 js" id="wpcf7-f6247-o1" lang="vi" dir="ltr">
                    <form action="/#wpcf7-f6247-o1" method="post" className="wpcf7-form init" aria-label="Form liên hệ">
                      <div className="dt-form-dk">
                        <p>
                          <span className="wpcf7-form-control-wrap" data-name="nt-hoten"><input size="40" className="wpcf7-form-control wpcf7-text wpcf7-validates-as-required effect-8" aria-required="true" placeholder="Họ và tên" type="text" name="nt-hoten" /></span><br />
                          <span className="wpcf7-form-control-wrap" data-name="nt-email"><input size="40" className="wpcf7-form-control wpcf7-text wpcf7-email wpcf7-validates-as-required wpcf7-validates-as-email effect-8" aria-required="true" placeholder="Email" type="email" name="nt-email" /></span><br />
                          <span className="wpcf7-form-control-wrap" data-name="noidung"><textarea cols="40" rows="1" className="wpcf7-form-control wpcf7-textarea wpcf7-validates-as-required effect-8" aria-required="true" placeholder="Nội dung" name="noidung"></textarea></span>
                        </p>
                        <p><input className="wpcf7-form-control has-spinner wpcf7-submit effect-8" type="submit" value="Gửi" /></p>
                      </div>
                    </form>
                  </div>
                </div>
              </div>
            </div>
            <div className="footer-links">
              <div className="footer-column">
                <h4 className="footer-title">Liên kết</h4>
                <ul>
                  <li><a href="https://ut.edu.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Trang chủ Trường</a></li>
                  <li><a href="https://moet.gov.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Bộ Giáo dục và Đào tạo</a></li>
                  <li><a href="https://tuyensinh.moet.gov.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Cổng thông tin tuyển sinh (Bộ GD&amp;ĐT)</a></li>
                  <li><a href="https://xaydung.gov.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Bộ Xây dựng</a></li>
                  <li><a href="https://daotao.ut.edu.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Phòng Đào tạo</a></li>
                  <li><a href="https://sdh.ut.edu.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Viện Đào tạo Sau đại học</a></li>
                  <li><a href="https://iec.ut.edu.vn" target="_blank" rel="noopener noreferrer"><i className="fa-regular fa-star" style={{ marginRight: '8px', fontSize: '12px' }}></i>Viện Đào tạo và Hợp tác quốc tế</a></li>
                </ul>
              </div>
            </div>
            <div className="footer-social">
              <h4 className="footer-title">Mạng xã hội</h4>
              <div className="social-links">
                <a href="https://www.facebook.com/TruongDHGiaothongvantaiTPHCM" target="_blank" rel="noopener noreferrer" className="social-link facebook" aria-label="Fanpage UTH">
                  <i className="fa-brands fa-square-facebook" />
                  <span>Fanpage</span>
                </a>
                <a href="https://www.youtube.com/TruongDHGiaothongvantaiTPHCM" target="_blank" rel="noopener noreferrer" className="social-link youtube" aria-label="Youtube UTH">
                  <i className="fa-brands fa-square-youtube" />
                  <span>Youtube</span>
                </a>
              </div>
              <div style={{ marginTop: '16px', fontSize: '14px', color: '#475569' }}>
                <p>❣ 𝐙𝐚𝐥𝐨 𝐎𝐀: <a href="https://zalo.me/tuyensinhuth" target="_blank" rel="noopener noreferrer" style={{ color: '#1ea59a', textDecoration: 'none', fontWeight: '500' }}>Tuyển Sinh Đại học GTVT TP HCM trên Zalo</a></p>
              </div>
            </div>
          </div>
          <div className="footer-bottom">
            <p className="copyright">Copyright © 2026 Chatbot tuyển sinh UTH - Đại học Giao thông vận tải TP.HCM - All rights reserved</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default TrangGioiThieu;
