document.addEventListener('DOMContentLoaded', () => {
    // --- Mobile Navigation ---
    const burger = document.getElementById('burger');
    const mobileNav = document.getElementById('mobileNav');

    // Toggle menu
    burger.addEventListener('click', () => {
        const isOpen = mobileNav.style.display === 'block';
        mobileNav.style.display = isOpen ? 'none' : 'block';
        burger.setAttribute('aria-expanded', !isOpen);
        document.body.style.overflow = isOpen ? '' : 'hidden'; // Lock scroll
    });

    // Close menu when clicking a link
    mobileNav.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileNav.style.display = 'none';
            document.body.style.overflow = '';
        });
    });

    // --- Calculator Logic ---
    const photoInputs = document.querySelectorAll('.photo-input');

    // File Upload Preview
    photoInputs.forEach(input => {
        input.addEventListener('change', function (e) {
            const file = e.target.files[0];
            const parent = input.parentElement;
            const preview = parent.querySelector('.photo-preview');
            const content = parent.querySelector('.photo-upload-content');

            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    preview.src = e.target.result;
                    preview.hidden = false;
                    content.style.opacity = '0'; // Hide label/icon
                }
                reader.readAsDataURL(file);
            } else {
                preview.hidden = true;
                preview.src = '';
                content.style.opacity = '1';
            }
        });
    });

    // Dummy Calculation (Enhance with real logic if needed)
    const calcForm = document.getElementById('calcForm');
    const resultValue = document.querySelector('.calc-result__value');

    const calculatePrice = () => {
        const lengthSelect = document.querySelector('select[name="length"]');
        const colorSelect = document.querySelector('select[name="color"]');
        const structureSelect = document.querySelector('select[name="structure"]');

        const length = lengthSelect ? lengthSelect.value : '';
        const color = colorSelect ? colorSelect.value : '';
        const structure = structureSelect ? structureSelect.value : '';

        // PRICE TABLE (Exact copy from main.py)
        const PRICE_TABLE = {
            '40-50': {
                'блонд': { 'славянка': 25000, 'среднее': 20000, 'густые': 25000 },
                'светло-русые': { 'славянка': 25000, 'среднее': 20000, 'густые': 25000 },
                'русые': { 'славянка': 20000, 'среднее': 18000, 'густые': 20000 },
                'темно-русые': { 'славянка': 20000, 'среднее': 18000, 'густые': 20000 },
                'каштановые': { 'славянка': 20000, 'среднее': 18000, 'густые': 20000 },
            },
            '50-60': {
                'блонд': { 'славянка': 35000, 'среднее': 30000, 'густые': 35000 },
                'светло-русые': { 'славянка': 35000, 'среднее': 30000, 'густые': 35000 },
                'русые': { 'славянка': 30000, 'среднее': 28000, 'густые': 30000 },
                'темно-русые': { 'славянка': 30000, 'среднее': 28000, 'густые': 30000 },
                'каштановые': { 'славянка': 28000, 'среднее': 25000, 'густые': 28000 },
            },
            '60-80': {
                'блонд': { 'славянка': 45000, 'среднее': 40000, 'густые': 45000 },
                'светло-русые': { 'славянка': 45000, 'среднее': 40000, 'густые': 45000 },
                'русые': { 'славянка': 40000, 'среднее': 38000, 'густые': 40000 },
                'темно-русые': { 'славянка': 40000, 'среднее': 38000, 'густые': 40000 },
                'каштановые': { 'славянка': 35000, 'среднее': 35000, 'густые': 38000 },
            },
            '80-100': {
                'блонд': { 'славянка': 55000, 'среднее': 50000, 'густые': 55000 },
                'светло-русые': { 'славянка': 55000, 'среднее': 50000, 'густые': 55000 },
                'русые': { 'славянка': 50000, 'среднее': 48000, 'густые': 50000 },
                'темно-русые': { 'славянка': 48000, 'среднее': 45000, 'густые': 48000 },
                'каштановые': { 'славянка': 48000, 'среднее': 45000, 'густые': 48000 },
            },
            '100+': {
                'блонд': { 'славянка': 65000, 'среднее': 60000, 'густые': 65000 },
                'светло-русые': { 'славянка': 65000, 'среднее': 60000, 'густые': 65000 },
                'русые': { 'славянка': 60000, 'среднее': 58000, 'густые': 60000 },
                'темно-русые': { 'славянка': 58000, 'среднее': 55000, 'густые': 58000 },
                'каштановые': { 'славянка': 55000, 'среднее': 55000, 'густые': 58000 },
            }
        };

        if (length && color && structure) {
            // 1. Normalize Length
            let lengthRange = '40-50'; // Default
            // Parse start number
            let lengthNum = 50;
            if (length === '70+') lengthNum = 70;
            else if (length.includes('-')) lengthNum = parseInt(length.split('-')[0]);

            if (lengthNum < 50) lengthRange = '40-50';
            else if (lengthNum < 60) lengthRange = '50-60';
            else if (lengthNum < 80) lengthRange = '60-80';
            else if (lengthNum < 100) lengthRange = '80-100';
            else lengthRange = '100+';

            // 2. Normalize Color
            const colorMap = {
                'blonde': 'блонд',
                'light-brown': 'русые',
                'brown': 'каштановые',
                'black': 'каштановые',
                'grey': 'русые',
                'red': 'каштановые'
            };
            const colorKey = colorMap[color] || 'блонд';

            // 3. Normalize Structure
            const structMap = {
                'straight': 'славянка',
                'wavy': 'среднее',
                'curly': 'густые'
            };
            const structKey = structMap[structure] || 'среднее';

            // 4. Lookup
            let price = 30000;
            try {
                price = PRICE_TABLE[lengthRange][colorKey][structKey];
            } catch (e) {
                console.error('Price lookup failed', e);
            }

            // Remove grams from display as requested
            resultValue.textContent = `~ ${price.toLocaleString('ru-RU')} ₽`;
        } else {
            resultValue.textContent = '-';
        }
    };

    // Calculate on input change
    calcForm.querySelectorAll('select, input').forEach(el => {
        el.addEventListener('change', calculatePrice);
        el.addEventListener('input', calculatePrice);
    });

    // Form Submission
    calcForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = calcForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;

        submitBtn.disabled = true;
        submitBtn.textContent = 'ОТПРАВКА...';

        const formData = new FormData(calcForm);

        // Manually append photos to the 'photos' list expected by FastAPI
        const photoInputs = calcForm.querySelectorAll('input[type="file"]');
        photoInputs.forEach(input => {
            if (input.files[0]) {
                formData.append('photos', input.files[0]);
            }
        });

        // Remove individual photo fields if they confuse the backend (optional, but cleaner)
        formData.delete('photo1');
        formData.delete('photo2');
        formData.delete('photo3');

        try {
            const response = await fetch('/api/calculate', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                alert('Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.');
                calcForm.reset();
                // Reset previews
                document.querySelectorAll('.photo-preview').forEach(img => {
                    img.hidden = true;
                    img.src = '';
                    img.parentElement.querySelector('.photo-upload-content').style.opacity = '1';
                });
                resultValue.textContent = '-';
            } else {
                alert('Произошла ошибка при отправке. Попробуйте еще раз.');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Ошибка соединения с сервером.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });

    // --- FAQ Auto-Slider ---
    const faqItems = document.querySelectorAll('.faq__item');
    const faqDots = document.querySelectorAll('.faq__pagination .dot');
    let currentFaqIndex = 0;
    let faqInterval;

    const showFaqItem = (index) => {
        if (!faqItems.length) return;
        faqItems.forEach(item => item.classList.remove('active'));
        faqDots.forEach(dot => dot.classList.remove('active'));

        faqItems[index].classList.add('active');
        if (faqDots[index]) faqDots[index].classList.add('active');
        currentFaqIndex = index;
    };

    const nextFaqItem = () => {
        if (!faqItems.length) return;
        const nextIndex = (currentFaqIndex + 1) % faqItems.length;
        showFaqItem(nextIndex);
    };

    if (faqItems.length > 0) {
        showFaqItem(0);
        faqInterval = setInterval(nextFaqItem, 5000);

        faqDots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                clearInterval(faqInterval);
                showFaqItem(index);
                faqInterval = setInterval(nextFaqItem, 5000);
            });
        });
    }

    // --- Footer Form Submission ---
    const footerForm = document.getElementById('footerForm');
    if (footerForm) {
        footerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = footerForm.querySelector('button');
            const originalText = btn.textContent;

            btn.disabled = true;
            btn.textContent = '...';

            const formData = new FormData(footerForm);

            try {
                const response = await fetch('/api/callback', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    alert('Мы перезвоним вам в ближайшее время!');
                    footerForm.reset();
                } else {
                    alert('Ошибка отправки.');
                }
            } catch (error) {
                console.error('Error:', error);
            } finally {
                btn.disabled = false;
                btn.textContent = originalText;
            }
        });
    }
});
