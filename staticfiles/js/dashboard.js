'use strict';

/* ============================================
   CARBONTRACK — Dashboard JavaScript
   Chart.js charts for data visualization
   ============================================ */

(function initDashboard() {
    // ---- Color Config ----
    const COLORS = {
        transport: '#3B82F6',
        energy: '#F59E0B',
        food: '#EF4444',
        shopping: '#8B5CF6',
        waste: '#6B7280',
        general: '#10B981',
    };

    const CATEGORY_LABELS = {
        transport: 'Transportation',
        energy: 'Home Energy',
        food: 'Food & Diet',
        shopping: 'Shopping',
        waste: 'Waste',
    };

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#CBD5E1' : '#64748B';
    const gridColor = isDark ? 'rgba(148, 163, 184, 0.1)' : 'rgba(0, 0, 0, 0.06)';

    // Chart.js global defaults
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.font.size = 13;
        Chart.defaults.color = textColor;
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 16;
    }

    // ---- Category Breakdown Doughnut Chart ----
    const categoryCanvas = document.getElementById('categoryChart');
    if (categoryCanvas && typeof Chart !== 'undefined') {
        const dataEl = document.getElementById('category-data');
        let categoryData = [];
        try {
            categoryData = JSON.parse(dataEl ? dataEl.textContent : '[]');
        } catch (e) { console.error('Failed to parse category data:', e); }

        const labels = categoryData.map(function(d) { return CATEGORY_LABELS[d.category] || d.category; });
        const values = categoryData.map(function(d) { return d.total; });
        const colors = categoryData.map(function(d) { return COLORS[d.category] || '#94A3B8'; });

        new Chart(categoryCanvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: isDark ? '#1E293B' : '#FFFFFF',
                    borderWidth: 3,
                    hoverBorderWidth: 0,
                    hoverOffset: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 16, font: { size: 12, weight: '500' } }
                    },
                    tooltip: {
                        backgroundColor: isDark ? '#334155' : '#1E293B',
                        titleFont: { weight: '600' },
                        bodyFont: { size: 13 },
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(ctx) {
                                return ctx.label + ': ' + ctx.parsed.toFixed(2) + ' kg CO₂';
                            }
                        }
                    }
                }
            }
        });
    }

    // ---- Trend Line Chart ----
    const trendCanvas = document.getElementById('trendChart');
    if (trendCanvas && typeof Chart !== 'undefined') {
        const dataEl = document.getElementById('trend-data');
        let trendData = [];
        try {
            trendData = JSON.parse(dataEl ? dataEl.textContent : '[]');
        } catch (e) { console.error('Failed to parse trend data:', e); }

        const labels = trendData.map(function(d) {
            const date = new Date(d.day || d.date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        const values = trendData.map(function(d) { return d.total; });

        new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'CO₂ Emissions (kg)',
                    data: values,
                    borderColor: '#10B981',
                    backgroundColor: function(ctx) {
                        const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, 350);
                        gradient.addColorStop(0, 'rgba(16, 185, 129, 0.25)');
                        gradient.addColorStop(1, 'rgba(16, 185, 129, 0.02)');
                        return gradient;
                    },
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#10B981',
                    pointBorderColor: '#FFFFFF',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDark ? '#334155' : '#1E293B',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(ctx) {
                                return ctx.parsed.y.toFixed(2) + ' kg CO₂';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 10 }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: {
                            callback: function(val) { return val + ' kg'; }
                        }
                    }
                }
            }
        });
    }

    // ---- Comparison Bar Chart ----
    const comparisonCanvas = document.getElementById('comparisonChart');
    if (comparisonCanvas && typeof Chart !== 'undefined') {
        const dataEl = document.getElementById('comparison-data');
        let compData = {};
        try {
            compData = JSON.parse(dataEl ? dataEl.textContent : '{}');
        } catch (e) { console.error('Failed to parse comparison data:', e); }

        new Chart(comparisonCanvas, {
            type: 'bar',
            data: {
                labels: ['You (Yearly Est.)', 'India Avg', 'Global Avg', 'EU Avg', 'US Avg'],
                datasets: [{
                    label: 'kg CO₂ per year',
                    data: [
                        compData.user_yearly || 0,
                        compData.india_avg || 1900,
                        compData.global_avg || 4700,
                        compData.eu_avg || 6800,
                        compData.us_avg || 15200,
                    ],
                    backgroundColor: [
                        '#10B981',
                        '#F59E0B',
                        '#3B82F6',
                        '#8B5CF6',
                        '#EF4444',
                    ],
                    borderRadius: 8,
                    borderSkipped: false,
                    maxBarThickness: 50,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: isDark ? '#334155' : '#1E293B',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(ctx) {
                                return ctx.parsed.x.toLocaleString() + ' kg CO₂/year';
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: gridColor },
                        ticks: {
                            callback: function(val) { return val.toLocaleString(); }
                        }
                    },
                    y: {
                        grid: { display: false },
                    }
                }
            }
        });
    }

    // ---- Animated Stat Values ----
    document.querySelectorAll('.dashboard-stat-value').forEach(function(el) {
        const target = parseFloat(el.dataset.value) || 0;
        const suffix = el.dataset.suffix || '';
        const decimals = parseInt(el.dataset.decimals) || 0;
        animateValue(el, target, suffix, decimals);
    });

    function animateValue(el, target, suffix, decimals) {
        const duration = 1500;
        const start = performance.now();

        function update(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = eased * target;

            el.textContent = current.toFixed(decimals) + suffix;

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = target.toFixed(decimals) + suffix;
            }
        }
        requestAnimationFrame(update);
    }
})();
