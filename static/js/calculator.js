'use strict';

/* ============================================
   CARBONTRACK — Calculator JavaScript
   Dynamic subcategory loading, real-time
   CO2 preview, form validation
   ============================================ */

(function initCalculator() {
    const categorySelect = document.getElementById('calc-category');
    const subCategorySelect = document.getElementById('calc-subcategory');
    const valueInput = document.getElementById('calc-value');
    const co2Preview = document.querySelector('.co2-value');
    const unitLabel = document.querySelector('.unit-label');
    const form = document.querySelector('.calculator-form form');

    if (!categorySelect || !subCategorySelect) return;

    let currentFactor = 0;
    let currentUnit = '';

    // ---- Fetch Subcategories ----
    categorySelect.addEventListener('change', function() {
        const category = this.value;
        if (!category) {
            resetSubcategories();
            return;
        }

        // Fetch subcategories from API
        fetch('/calculator/api/subcategories/' + category + '/')
            .then(function(res) { return res.json(); })
            .then(function(data) {
                subCategorySelect.innerHTML = '<option value="">Select Sub-category</option>';
                data.forEach(function(item) {
                    const option = document.createElement('option');
                    option.value = item.value;
                    option.textContent = item.label;
                    option.dataset.factor = item.factor;
                    option.dataset.unit = item.unit;
                    subCategorySelect.appendChild(option);
                });
                subCategorySelect.disabled = false;
                subCategorySelect.focus();
            })
            .catch(function(err) {
                console.error('Failed to load subcategories:', err);
            });

        // Highlight active category info card
        document.querySelectorAll('.category-info-card').forEach(function(card) {
            card.classList.toggle('active', card.dataset.category === category);
        });
    });

    // ---- Subcategory Change → Update Unit & Factor ----
    subCategorySelect.addEventListener('change', function() {
        const selected = this.options[this.selectedIndex];
        if (selected && selected.value) {
            currentFactor = parseFloat(selected.dataset.factor) || 0;
            currentUnit = selected.dataset.unit || 'unit';
            if (unitLabel) {
                unitLabel.textContent = currentUnit;
            }
            updatePreview();
        } else {
            currentFactor = 0;
            currentUnit = '';
            if (unitLabel) unitLabel.textContent = 'unit';
            updatePreview();
        }
    });

    // ---- Real-time CO2 Preview ----
    if (valueInput) {
        valueInput.addEventListener('input', updatePreview);
        valueInput.addEventListener('change', updatePreview);
    }

    function updatePreview() {
        const value = parseFloat(valueInput ? valueInput.value : 0) || 0;
        const co2 = (value * currentFactor).toFixed(2);
        if (co2Preview) {
            co2Preview.textContent = co2;
            // Animate the value change
            co2Preview.classList.remove('animate-fade-in');
            void co2Preview.offsetWidth; // Force reflow
            co2Preview.classList.add('animate-fade-in');
        }
    }

    function resetSubcategories() {
        subCategorySelect.innerHTML = '<option value="">Select Sub-category</option>';
        subCategorySelect.disabled = true;
        currentFactor = 0;
        currentUnit = '';
        if (unitLabel) unitLabel.textContent = 'unit';
        updatePreview();
    }

    // ---- Category Info Cards Click ----
    document.querySelectorAll('.category-info-card').forEach(function(card) {
        card.addEventListener('click', function() {
            const category = this.dataset.category;
            if (category && categorySelect) {
                categorySelect.value = category;
                categorySelect.dispatchEvent(new Event('change'));
            }
        });
    });

    // ---- Form Validation ----
    if (form) {
        form.addEventListener('submit', function(e) {
            let valid = true;
            const category = categorySelect.value;
            const subCategory = subCategorySelect.value;
            const value = valueInput ? parseFloat(valueInput.value) : 0;

            if (!category) {
                showFieldError(categorySelect, 'Please select a category');
                valid = false;
            }
            if (!subCategory) {
                showFieldError(subCategorySelect, 'Please select a sub-category');
                valid = false;
            }
            if (!value || value <= 0) {
                showFieldError(valueInput, 'Please enter a valid amount');
                valid = false;
            }

            if (!valid) {
                e.preventDefault();
            }
        });
    }

    function showFieldError(field, message) {
        clearFieldError(field);
        field.classList.add('error');
        const errDiv = document.createElement('div');
        errDiv.className = 'form-error';
        errDiv.setAttribute('role', 'alert');
        errDiv.textContent = message;
        field.parentNode.appendChild(errDiv);
    }

    function clearFieldError(field) {
        field.classList.remove('error');
        const existing = field.parentNode.querySelector('.form-error');
        if (existing) existing.remove();
    }

    // Clear errors on input
    [categorySelect, subCategorySelect, valueInput].forEach(function(field) {
        if (field) {
            field.addEventListener('change', function() { clearFieldError(this); });
            field.addEventListener('input', function() { clearFieldError(this); });
        }
    });
})();
