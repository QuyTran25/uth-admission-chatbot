import React from 'react';
import '../CSS/Footer.css';

const Footer = ({ minimal }) => {
  return (
    <footer className="footer">
      <div className="footer-container">
        {!minimal && (
          <div className="footer-main">
            <div className="footer-brand">
              <img src="/images/logo-full.png" alt="UTH Logo" className="footer-logo" />
              <p className="footer-tagline">Trường Đại học Giao thông vận tải TP. Hồ Chí Minh</p>
              {/* Contact Form placeholder as seen in JSX */}
              <div id="text-36" className="widget single-sidebar widget_text">
                <h2 className="widget-title">LIÊN HỆ</h2>
                <div className="textwidget">
                  <div className="wpcf7 js" id="wpcf7-f6247-o1">
                    <form action="/#wpcf7-f6247-o1" method="post" className="wpcf7-form init">
                      <div className="dt-form-dk">
                        <p>
                          <span className="wpcf7-form-control-wrap"><input className="wpcf7-form-control wpcf7-text effect-8" placeholder="Họ và tên" type="text" name="nt-hoten" /></span><br />
                          <span className="wpcf7-form-control-wrap"><input className="wpcf7-form-control wpcf7-text wpcf7-email effect-8" placeholder="Email" type="email" name="nt-email" /></span><br />
                          <span className="wpcf7-form-control-wrap"><textarea className="wpcf7-form-control wpcf7-textarea effect-8" placeholder="Nội dung" name="noidung"></textarea></span>
                        </p>
                        <p><input className="wpcf7-form-control wpcf7-submit effect-8" type="submit" value="Gửi" /></p>
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
        )}
        <div className="footer-bottom">
          <p className="copyright">Copyright © 2026 Chatbot tuyển sinh UTH - Đại học Giao thông vận tải TP.HCM - All rights reserved</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
