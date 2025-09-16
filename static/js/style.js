// إصلاح مشاكل اتجاه النص للعربية
document.addEventListener('DOMContentLoaded', function() {
    // تأكد من أن الصفحة في وضع RTL
    document.documentElement.setAttribute('dir', 'rtl');
    document.documentElement.setAttribute('lang', 'ar');
    
    // إصلاح اتجاه عناصر محددة
    const fixDirection = () => {
        // العناصر التي يجب أن تبقى LTR
        const ltrElements = document.querySelectorAll('.logo, .search-input, .search-btn, .top-bar span');
        ltrElements.forEach(el => {
            el.style.direction = 'ltr';
            el.style.textAlign = 'left';
        });
        
        // العناصر التي يجب أن تكون RTL
        const rtlElements = document.querySelectorAll('nav, main, footer, .product-info');
        rtlElements.forEach(el => {
            el.style.direction = 'rtl';
            el.style.textAlign = 'right';
        });
    };
    
    fixDirection();
});
