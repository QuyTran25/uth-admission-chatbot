import React from 'react';
import Header from './Header.jsx';
import './CSS/Global.css';
import './CSS/HeroSection.css';
import './CSS/VideoSection.css';
import './CSS/StatisticsSection.css';
import './CSS/DiscoverySection.css';
import './CSS/ContactSection.css';
import './CSS/CTASection.css';
import './CSS/Footer.css';

const TrangGioiThieu = () => {
  const scrollToContact = () => {
    document.querySelector('.contact-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  const playVideo = () => {
    const video = document.getElementById('campusVideo');
    if (video) {
      if (video.paused) {
        video.play().catch(() => {
          window.open('https://www.youtube.com/watch?v=dQw4w9WgXcQ', '_blank');
        });
      }
    }
  };

  return (
    <div className="page-wrapper">
      <Header />
      {/* Hero Section */}
      <section className="hero-section" aria-labelledby="hero-title">
        <div className="container">
          <img
            src="/images/hero-illustration.png"
            alt="Minh họa AI Assistant của UTH"
            className="hero-illustration"
          />
          <div className="hero-content">
            <h1 id="hero-title" className="hero-title">
              <span className="title-dark">Trợ lý</span>
              <span className="title-primary">tuyển sinh</span>
            </h1>

            <p className="hero-subtitle">
              Trường Đại học Giao thông vận tải TP. Hồ Chí Minh
            </p>

            <div className="hero-actions">
              <button className="btn btn-primary" onClick={scrollToContact}>
                Trò chuyện với trợ lý
              </button>

              <p className="hero-actions-hint">
                Tư vấn 24/7, đa dạng thông tin
              </p>
            </div>

            <div className="welcome-container">
              <h2 className="welcome-title">WELCOME TO UTH</h2>
            </div>
          </div>
        </div>
      </section>

      {/* Video Introduction Section */}
      <section id="video-section" className="video-section" aria-labelledby="video-title">
        <div className="video-container">
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

      {/* Statistics Section */}
      <section className="statistics-section" aria-labelledby="stats-title">
        <div className="container">
          <h2 id="stats-title" className="section-title">Số liệu ấn tượng</h2>
          <div className="stats-grid">
            <article className="stat-card">
              <div className="stat-number">35+</div>
              <div className="stat-title">Năm hình thành & Phát triển</div>
              <p className="stat-description">Hành trình hơn ba thập kỷ đào tạo nhân lực chất lượng cao cho ngành giao thông vận tải.</p>
            </article>
            <article className="stat-card">
              <div className="stat-number">50+</div>
              <div className="stat-title">Câu lạc bộ sinh viên</div>
              <p className="stat-description">Môi trường năng động giúp sinh viên phát triển kỹ năng mềm, nghệ thuật và thể thao.</p>
            </article>
            <article className="stat-card">
              <div className="stat-number">6</div>
              <div className="stat-title">Cơ sở đào tạo chính quy hiện đại</div>
              <p className="stat-description">Hệ thống cơ sở trải dài từ TP.HCM, Vũng Tàu đến Đồng Nai với trang thiết bị tiên tiến.</p>
            </article>
          </div>
        </div>
      </section>

      {/* Discovery Grid Section */}
      <section className="discovery-section" aria-labelledby="discovery-title">
        <div className="container">
          <h2 id="discovery-title" className="section-title">Khám phá <span>UTH</span></h2>
          <div className="discovery-grid">
            <a href="#contact" className="discovery-card-link">
              <article className="discovery-card">
                <img className="discovery-image" src="/icons/discovery-contact.png" alt="Thông tin liên hệ UTH" />
                <div className="discovery-overlay">
                  <div className="discovery-content">
                    <i className="fa-solid fa-phone discovery-icon"></i>
                    <h3 className="discovery-title">Thông tin liên hệ</h3>
                  </div>
                </div>
              </article>
            </a>
            <a href="#contact" className="discovery-card-link">
              <article className="discovery-card">
                <img className="discovery-image" src="/icons/discovery-web.png" alt="Website UTH" />
                <div className="discovery-overlay">
                  <div className="discovery-content">
                    <i className="fa-solid fa-globe discovery-icon"></i>
                    <h3 className="discovery-title">Website UTH</h3>
                  </div>
                </div>
              </article>
            </a>
            <a href="#video-section" className="discovery-card-link">
              <article className="discovery-card">
                <img className="discovery-image" src="/icons/discovery-video.png" alt="Video giới thiệu UTH" />
                <div className="discovery-overlay">
                  <div className="discovery-content">
                    <i className="fa-solid fa-video discovery-icon"></i>
                    <h3 className="discovery-title">Video giới thiệu</h3>
                  </div>
                </div>
              </article>
            </a>
          </div>
        </div>
      </section>

      {/* Contact Section */}
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
                    <i className="fa-solid fa-location-dot"></i>
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
                    <i className="fa-regular fa-envelope"></i>
                  </div>
                  <div className="contact-info-content">
                    <span className="contact-info-label">Tuyển sinh</span>
                    <div className="contact-info-list">
                      <div className="contact-info-value">
                        <span className="contact-info-text">Hotline: 028 3899 6199</span>
                      </div>
                      <div className="contact-info-value">
                        <span className="contact-info-text">Email: tuyensinh@uth.edu.vn</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="contact-info-item">
                  <div className="contact-icon-wrapper">
                    <i className="fa-solid fa-globe"></i>
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
                <i className="fa-regular fa-comment"></i>
              </button>
              <div className="cta-text">
                <h2 id="cta-title" className="cta-title">
                  Luôn sẵn sàng hỗ trợ bạn <br />
                  mọi lúc
                </h2>
              </div>
            </div>
            <button className="cta-start-btn">Bắt đầu</button>
          </div>
        </div>
      </section>

      {/* Footer Section */}
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
                  <i className="fa-brands fa-square-facebook"></i>
                  <span>Fanpage</span>
                </a>
                <a href="https://www.youtube.com/TruongDHGiaothongvantaiTPHCM" target="_blank" rel="noopener noreferrer" className="social-link youtube" aria-label="Youtube UTH">
                  <i className="fa-brands fa-square-youtube"></i>
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
