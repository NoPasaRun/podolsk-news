import React, { useState, useEffect } from 'react';

const ScrollToTopButton = () => {
  const [showButton, setShowButton] = useState(false);

  // Функция для прокрутки страницы вверх
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Отслеживание прокрутки страницы
  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 300) { // Показать кнопку, если прокрутили больше чем на 300px
        setShowButton(true);
      } else {
        setShowButton(false);
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      {showButton && (
        <button 
          onClick={scrollToTop} 
          style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            padding: '10px 10px',
            fontSize: '16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '50%',
            cursor: 'pointer',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            transition: 'opacity 0.3s',
            opacity: showButton ? 1 : 0,
          }}
        >
        <svg width="30px" height="30px" viewBox="0 0 20 20" fill="none">
            <path stroke="#fff" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 18V2m0 0l7 7m-7-7L3 9"/>
        </svg>
        </button>
      )}
    </>
  );
};

export default ScrollToTopButton;