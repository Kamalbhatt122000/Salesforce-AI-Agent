/**
 * A2UI (Agent-to-User Interface) Renderer
 * ════════════════════════════════════════
 * A lightweight client-side renderer that implements the A2UI v0.8 spec
 * for rendering declarative UI surfaces from agent-generated JSON.
 *
 * This renderer supports the following A2UI component catalog:
 *   Standard:  Card, Column, Row, Text, Divider
 *   Custom:    Chart (bar, pie, doughnut, line, horizontalBar)
 *
 * Reference: https://github.com/google/A2UI
 */

// ── A2UI Message Processor ──────────────────────────────────
class A2UIMessageProcessor {
    constructor() {
        // Map<surfaceId, { components: Map<id, componentDef>, dataModel: object, root: string, catalogId: string }>
        this.surfaces = new Map();
    }

    /**
     * Process a list of A2UI messages (JSONL-like array).
     * Each message is one of: surfaceUpdate, dataModelUpdate, beginRendering, deleteSurface
     */
    processMessages(messages) {
        if (!Array.isArray(messages)) {
            messages = [messages];
        }

        for (const msg of messages) {
            const surfaceId = msg.surfaceId || 'default';

            if (!this.surfaces.has(surfaceId)) {
                this.surfaces.set(surfaceId, {
                    components: new Map(),
                    dataModel: {},
                    root: null,
                    catalogId: null,
                });
            }

            const surface = this.surfaces.get(surfaceId);

            if (msg.surfaceUpdate) {
                this._handleSurfaceUpdate(surface, msg.surfaceUpdate);
            }
            if (msg.dataModelUpdate) {
                this._handleDataModelUpdate(surface, msg.dataModelUpdate);
            }
            if (msg.beginRendering) {
                this._handleBeginRendering(surface, msg.beginRendering);
            }
            if (msg.deleteSurface) {
                this.surfaces.delete(surfaceId);
            }
        }
    }

    _handleSurfaceUpdate(surface, update) {
        if (update.components) {
            for (const comp of update.components) {
                surface.components.set(comp.id, comp.component);
            }
        }
    }

    _handleDataModelUpdate(surface, update) {
        if (update.contents) {
            surface.dataModel = this._deepMerge(surface.dataModel, update.contents);
        }
    }

    _handleBeginRendering(surface, rendering) {
        surface.root = rendering.root;
        if (rendering.catalogId) {
            surface.catalogId = rendering.catalogId;
        }
    }

    _deepMerge(target, source) {
        const output = { ...target };
        for (const key of Object.keys(source)) {
            if (
                source[key] &&
                typeof source[key] === 'object' &&
                !Array.isArray(source[key]) &&
                target[key] &&
                typeof target[key] === 'object'
            ) {
                output[key] = this._deepMerge(target[key], source[key]);
            } else {
                output[key] = source[key];
            }
        }
        return output;
    }

    getSurface(surfaceId = 'default') {
        return this.surfaces.get(surfaceId) || null;
    }
}


// ── A2UI Component Registry (Catalog) ───────────────────────
const A2UI_CATALOG = {};

/**
 * Register a component renderer with the A2UI catalog.
 * @param {string} typeName - Component type name (e.g. 'Text', 'Card', 'Chart')
 * @param {Function} renderFn - (props, context) => HTMLElement
 */
function registerA2UIComponent(typeName, renderFn) {
    A2UI_CATALOG[typeName] = renderFn;
}


// ── A2UI Renderer ───────────────────────────────────────────
class A2UIRenderer {
    constructor(processor) {
        this.processor = processor;
        this.chartCounter = 0;
    }

    /**
     * Render a surface into a DOM container.
     * @param {string} surfaceId
     * @returns {HTMLElement|null}
     */
    renderSurface(surfaceId = 'default') {
        const surface = this.processor.getSurface(surfaceId);
        if (!surface || !surface.root) return null;

        const rootComp = surface.components.get(surface.root);
        if (!rootComp) return null;

        const context = {
            surface,
            components: surface.components,
            dataModel: surface.dataModel,
            renderer: this,
        };

        return this._renderComponent(surface.root, rootComp, context);
    }

    _renderComponent(id, componentDef, context) {
        // componentDef is { "TypeName": { ...props } }
        const typeName = Object.keys(componentDef)[0];
        const props = componentDef[typeName];

        const renderFn = A2UI_CATALOG[typeName];
        if (!renderFn) {
            console.warn(`[A2UI] Unknown component type: ${typeName}`);
            const fallback = document.createElement('div');
            fallback.className = 'a2ui-unknown';
            fallback.textContent = `[Unknown: ${typeName}]`;
            return fallback;
        }

        return renderFn(props, { ...context, componentId: id });
    }

    renderChildById(childId, context) {
        const componentDef = context.components.get(childId);
        if (!componentDef) {
            console.warn(`[A2UI] Child component not found: ${childId}`);
            return document.createElement('span');
        }
        return this._renderComponent(childId, componentDef, context);
    }

    /**
     * Resolve a BoundValue — either literalString or dataModelPath
     */
    resolveValue(valueDef, context) {
        if (!valueDef) return '';
        if (typeof valueDef === 'string') return valueDef;
        if (valueDef.literalString !== undefined) return valueDef.literalString;
        if (valueDef.literalNumber !== undefined) return valueDef.literalNumber;
        if (valueDef.literalBool !== undefined) return valueDef.literalBool;
        if (valueDef.dataModelPath) {
            return this._resolveJsonPointer(context.dataModel, valueDef.dataModelPath);
        }
        // If it's a plain value, return as-is
        if (typeof valueDef === 'number' || typeof valueDef === 'boolean') return valueDef;
        return String(valueDef);
    }

    _resolveJsonPointer(obj, pointer) {
        if (!pointer || pointer === '/') return obj;
        const parts = pointer.replace(/^\//, '').split('/');
        let current = obj;
        for (const part of parts) {
            if (current === undefined || current === null) return undefined;
            current = current[part];
        }
        return current;
    }

    getNextChartId() {
        return `a2ui-chart-${++this.chartCounter}`;
    }
}


// ── Standard Component Implementations ──────────────────────

// ── Text ──
registerA2UIComponent('Text', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-text';
    const text = context.renderer.resolveValue(props.text, context);

    if (props.usageHint === 'h1') {
        el.innerHTML = `<h2 class="a2ui-heading-1">${escapeA2Html(text)}</h2>`;
    } else if (props.usageHint === 'h2') {
        el.innerHTML = `<h3 class="a2ui-heading-2">${escapeA2Html(text)}</h3>`;
    } else if (props.usageHint === 'h3') {
        el.innerHTML = `<h4 class="a2ui-heading-3">${escapeA2Html(text)}</h4>`;
    } else if (props.usageHint === 'subtitle' || props.usageHint === 'caption') {
        el.innerHTML = `<span class="a2ui-subtitle">${escapeA2Html(text)}</span>`;
    } else if (props.usageHint === 'label') {
        el.innerHTML = `<span class="a2ui-label">${escapeA2Html(text)}</span>`;
    } else {
        el.innerHTML = `<span class="a2ui-body">${escapeA2Html(text)}</span>`;
    }

    if (props.style) {
        if (props.style.color) el.style.color = props.style.color;
        if (props.style.fontWeight) el.style.fontWeight = props.style.fontWeight;
        if (props.style.fontSize) el.style.fontSize = props.style.fontSize;
        if (props.style.textAlign) el.style.textAlign = props.style.textAlign;
    }

    return el;
});

// ── Column ──
registerA2UIComponent('Column', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-column';

    if (props.alignment) {
        el.classList.add(`a2ui-align-${props.alignment}`);
    }
    if (props.gap) {
        el.style.gap = typeof props.gap === 'number' ? `${props.gap}px` : props.gap;
    }

    const children = getChildIds(props);
    for (const childId of children) {
        el.appendChild(context.renderer.renderChildById(childId, context));
    }

    return el;
});

// ── Row ──
registerA2UIComponent('Row', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-row';

    if (props.alignment) {
        el.classList.add(`a2ui-align-${props.alignment}`);
    }
    if (props.gap) {
        el.style.gap = typeof props.gap === 'number' ? `${props.gap}px` : props.gap;
    }

    const children = getChildIds(props);
    for (const childId of children) {
        el.appendChild(context.renderer.renderChildById(childId, context));
    }

    return el;
});

// ── Card ──
registerA2UIComponent('Card', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-card';

    if (props.elevation) {
        el.classList.add(`a2ui-elevation-${props.elevation}`);
    }

    if (props.child) {
        el.appendChild(context.renderer.renderChildById(props.child, context));
    }

    const children = getChildIds(props);
    for (const childId of children) {
        el.appendChild(context.renderer.renderChildById(childId, context));
    }

    return el;
});

// ── Divider ──
registerA2UIComponent('Divider', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-divider';
    return el;
});

// ── Image ──
registerA2UIComponent('Image', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-image';
    const url = context.renderer.resolveValue(props.url, context);
    if (url) {
        const img = document.createElement('img');
        img.src = url;
        img.alt = context.renderer.resolveValue(props.alt, context) || '';
        el.appendChild(img);
    }
    return el;
});

// ── Icon ──
registerA2UIComponent('Icon', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-icon';
    const name = context.renderer.resolveValue(props.name, context);
    el.innerHTML = getIconSvg(name);
    if (props.size) el.style.fontSize = `${props.size}px`;
    if (props.color) el.style.color = props.color;
    return el;
});

// ── Spacer ──
registerA2UIComponent('Spacer', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-spacer';
    if (props.height) el.style.height = `${props.height}px`;
    if (props.width) el.style.width = `${props.width}px`;
    return el;
});

// ── Badge ──
registerA2UIComponent('Badge', (props, context) => {
    const el = document.createElement('span');
    el.className = 'a2ui-badge';
    const text = context.renderer.resolveValue(props.text || props.label, context);
    el.textContent = text;
    if (props.color) {
        el.style.background = props.color + '22';
        el.style.color = props.color;
        el.style.borderColor = props.color + '44';
    }
    return el;
});


// ── CUSTOM: Chart Component ─────────────────────────────────
// This is a custom A2UI catalog component for rendering charts.
// The agent generates Chart component data, and the client renders
// it using Chart.js — following A2UI's philosophy of safe, declarative UI.

const A2UI_CHART_COLORS = [
    '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
    '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#3b82f6',
    '#84cc16', '#a855f7', '#e11d48', '#0ea5e9', '#22c55e',
];

const A2UI_CHART_BG_COLORS = A2UI_CHART_COLORS.map(c => c + '33');

registerA2UIComponent('Chart', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-chart-surface';

    // Resolve data-bound or literal values
    const chartType = context.renderer.resolveValue(props.chartType || props.chart_type, context) || 'bar';
    const title = context.renderer.resolveValue(props.title, context) || 'Chart';
    const datasetLabel = context.renderer.resolveValue(props.datasetLabel || props.dataset_label, context) || 'Count';

    // Resolve labels and data arrays
    let labels = props.labels || [];
    let data = props.data || [];

    if (labels.dataModelPath) {
        labels = context.renderer.resolveValue(labels, context) || [];
    } else if (Array.isArray(labels)) {
        labels = labels.map(l => context.renderer.resolveValue(l, context));
    }
    if (data.dataModelPath) {
        data = context.renderer.resolveValue(data, context) || [];
    } else if (Array.isArray(data)) {
        data = data.map(d => {
            const v = context.renderer.resolveValue(d, context);
            return typeof v === 'number' ? v : parseFloat(v) || 0;
        });
    }

    // Chart header with gradient accent
    const header = document.createElement('div');
    header.className = 'a2ui-chart-header';
    header.innerHTML = `
        <div class="a2ui-chart-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"/>
                <line x1="12" y1="20" x2="12" y2="4"/>
                <line x1="6" y1="20" x2="6" y2="14"/>
            </svg>
        </div>
        <span class="a2ui-chart-title">${escapeA2Html(title)}</span>
        <span class="a2ui-chart-badge">A2UI</span>
    `;
    wrapper.appendChild(header);

    // Canvas wrapper
    const canvasWrapper = document.createElement('div');
    canvasWrapper.className = 'a2ui-chart-canvas-wrapper';
    const canvas = document.createElement('canvas');
    const chartId = context.renderer.getNextChartId();
    canvas.id = chartId;
    canvasWrapper.appendChild(canvas);
    wrapper.appendChild(canvasWrapper);

    // Build Chart.js config
    let jsChartType = chartType;
    let indexAxis = undefined;
    if (jsChartType === 'horizontalBar') {
        jsChartType = 'bar';
        indexAxis = 'y';
    }

    const isPieType = (jsChartType === 'pie' || jsChartType === 'doughnut');
    const totalValue = data.reduce((a, b) => a + b, 0);

    const dataset = {
        label: datasetLabel,
        data: data,
        borderWidth: isPieType ? 2 : 2,
        borderRadius: isPieType ? 0 : 6,
        borderSkipped: false,
    };

    if (isPieType) {
        dataset.backgroundColor = data.map((_, i) => A2UI_CHART_COLORS[i % A2UI_CHART_COLORS.length]);
        dataset.borderColor = '#0f0f1a';
    } else if (jsChartType === 'line') {
        dataset.borderColor = A2UI_CHART_COLORS[0];
        dataset.backgroundColor = A2UI_CHART_BG_COLORS[0];
        dataset.fill = true;
        dataset.tension = 0.4;
        dataset.pointBackgroundColor = A2UI_CHART_COLORS[0];
        dataset.pointBorderColor = '#fff';
        dataset.pointBorderWidth = 2;
        dataset.pointRadius = 5;
        dataset.pointHoverRadius = 7;
    } else {
        dataset.backgroundColor = data.map((_, i) => A2UI_CHART_COLORS[i % A2UI_CHART_COLORS.length]);
        dataset.borderColor = data.map((_, i) => A2UI_CHART_COLORS[i % A2UI_CHART_COLORS.length]);
    }

    // Smart datalabels config
    let datalabelsConfig;
    if (isPieType) {
        datalabelsConfig = {
            color: '#fff',
            font: { family: "'Inter', sans-serif", weight: '600', size: 12 },
            textShadowColor: 'rgba(0,0,0,0.5)',
            textShadowBlur: 4,
            formatter: (value) => {
                const pct = ((value / totalValue) * 100).toFixed(1);
                return `${value}\n(${pct}%)`;
            },
            display: (ctx) => {
                const pct = (ctx.dataset.data[ctx.dataIndex] / totalValue) * 100;
                return pct >= 5;
            },
            anchor: 'center',
            align: 'center',
            textAlign: 'center',
        };
    } else if (jsChartType === 'line') {
        datalabelsConfig = {
            color: '#e8e8f0',
            font: { family: "'Inter', sans-serif", weight: '600', size: 11 },
            anchor: 'end',
            align: 'top',
            offset: 4,
            formatter: (value) => value,
        };
    } else {
        datalabelsConfig = {
            color: '#e8e8f0',
            font: { family: "'Inter', sans-serif", weight: '600', size: 12 },
            anchor: 'end',
            align: indexAxis === 'y' ? 'right' : 'top',
            offset: 4,
            formatter: (value) => value,
        };
    }

    // Create chart after DOM attachment
    setTimeout(() => {
        const ctx = document.getElementById(chartId);
        if (!ctx) return;

        new Chart(ctx, {
            type: jsChartType,
            data: {
                labels: labels,
                datasets: [dataset],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: indexAxis || 'x',
                animation: {
                    duration: 1200,
                    easing: 'easeOutQuart',
                },
                layout: {
                    padding: { top: isPieType ? 10 : 24, right: indexAxis === 'y' ? 40 : 10 },
                },
                plugins: {
                    legend: {
                        display: isPieType,
                        position: 'bottom',
                        labels: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 12 },
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                        },
                    },
                    tooltip: {
                        backgroundColor: '#0f0f1a',
                        titleColor: '#e8e8f0',
                        bodyColor: '#9494a8',
                        borderColor: '#2a2a3a',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { family: "'Inter', sans-serif", weight: '600' },
                        bodyFont: { family: "'Inter', sans-serif" },
                        displayColors: true,
                        boxPadding: 4,
                        callbacks: isPieType ? {
                            label: (ctx) => {
                                const val = ctx.parsed;
                                const pct = ((val / totalValue) * 100).toFixed(1);
                                return ` ${ctx.label}: ${val} (${pct}%)`;
                            }
                        } : {},
                    },
                    datalabels: datalabelsConfig,
                },
                scales: isPieType ? {} : {
                    x: {
                        grid: { color: '#2a2a3a22', drawBorder: false },
                        ticks: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 11 },
                            maxRotation: 45,
                        },
                        border: { display: false },
                    },
                    y: {
                        grid: { color: '#2a2a3a44', drawBorder: false },
                        ticks: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 11 },
                            precision: 0,
                        },
                        border: { display: false },
                        beginAtZero: true,
                    },
                },
            },
        });
    }, 80);

    return wrapper;
});


// ── Multi-Dataset Chart (Grouped / Stacked) ─────────────────
registerA2UIComponent('MultiChart', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-chart-surface';

    const chartType = context.renderer.resolveValue(props.chartType || props.chart_type, context) || 'bar';
    const title = context.renderer.resolveValue(props.title, context) || 'Chart';
    const stacked = props.stacked === true;

    let labels = props.labels || [];
    if (labels.dataModelPath) {
        labels = context.renderer.resolveValue(labels, context) || [];
    } else if (Array.isArray(labels)) {
        labels = labels.map(l => context.renderer.resolveValue(l, context));
    }

    const header = document.createElement('div');
    header.className = 'a2ui-chart-header';
    header.innerHTML = `
        <div class="a2ui-chart-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="1" y="3" width="22" height="18" rx="2"/><line x1="1" y1="9" x2="23" y2="9"/>
                <line x1="8" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="16" y2="21"/>
            </svg>
        </div>
        <span class="a2ui-chart-title">${escapeA2Html(title)}</span>
        <span class="a2ui-chart-badge">A2UI</span>
    `;
    wrapper.appendChild(header);

    const canvasWrapper = document.createElement('div');
    canvasWrapper.className = 'a2ui-chart-canvas-wrapper';
    const canvas = document.createElement('canvas');
    const chartId = context.renderer.getNextChartId();
    canvas.id = chartId;
    canvasWrapper.appendChild(canvas);
    wrapper.appendChild(canvasWrapper);

    const datasets = (props.datasets || []).map((ds, i) => {
        let dsData = ds.data || [];
        if (Array.isArray(dsData)) {
            dsData = dsData.map(d => {
                const v = context.renderer.resolveValue(d, context);
                return typeof v === 'number' ? v : parseFloat(v) || 0;
            });
        }
        return {
            label: context.renderer.resolveValue(ds.label, context) || `Dataset ${i + 1}`,
            data: dsData,
            backgroundColor: A2UI_CHART_COLORS[i % A2UI_CHART_COLORS.length] + (chartType === 'line' ? '33' : ''),
            borderColor: A2UI_CHART_COLORS[i % A2UI_CHART_COLORS.length],
            borderWidth: 2,
            borderRadius: chartType === 'bar' ? 6 : 0,
            fill: chartType === 'line',
            tension: chartType === 'line' ? 0.4 : 0,
            pointRadius: chartType === 'line' ? 4 : 0,
        };
    });

    setTimeout(() => {
        const ctx = document.getElementById(chartId);
        if (!ctx) return;

        new Chart(ctx, {
            type: chartType === 'horizontalBar' ? 'bar' : chartType,
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: chartType === 'horizontalBar' ? 'y' : 'x',
                animation: { duration: 1200, easing: 'easeOutQuart' },
                layout: { padding: { top: 20 } },
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#9494a8',
                            font: { family: "'Inter', sans-serif", size: 12 },
                            padding: 16,
                            usePointStyle: true,
                        },
                    },
                    tooltip: {
                        backgroundColor: '#0f0f1a',
                        titleColor: '#e8e8f0',
                        bodyColor: '#9494a8',
                        borderColor: '#2a2a3a',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                    },
                    datalabels: { display: false },
                },
                scales: {
                    x: {
                        stacked,
                        grid: { color: '#2a2a3a22', drawBorder: false },
                        ticks: { color: '#9494a8', font: { family: "'Inter', sans-serif", size: 11 } },
                        border: { display: false },
                    },
                    y: {
                        stacked,
                        grid: { color: '#2a2a3a44', drawBorder: false },
                        ticks: { color: '#9494a8', font: { family: "'Inter', sans-serif", size: 11 }, precision: 0 },
                        border: { display: false },
                        beginAtZero: true,
                    },
                },
            },
        });
    }, 80);

    return wrapper;
});


// ── Stats Card Component ────────────────────────────────────
registerA2UIComponent('StatsCard', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-stats-card';

    const label = context.renderer.resolveValue(props.label, context) || '';
    const value = context.renderer.resolveValue(props.value, context) || '0';
    const trend = context.renderer.resolveValue(props.trend, context) || '';
    const color = props.color || '#6366f1';

    el.innerHTML = `
        <div class="a2ui-stats-accent" style="background: ${color}"></div>
        <div class="a2ui-stats-body">
            <div class="a2ui-stats-label">${escapeA2Html(label)}</div>
            <div class="a2ui-stats-value">${escapeA2Html(String(value))}</div>
            ${trend ? `<div class="a2ui-stats-trend" style="color: ${trend.startsWith('+') || trend.startsWith('↑') ? '#10b981' : '#ef4444'}">${escapeA2Html(trend)}</div>` : ''}
        </div>
    `;

    return el;
});


// ── Helpers ─────────────────────────────────────────────────

function getChildIds(props) {
    if (!props) return [];
    if (props.children) {
        if (props.children.explicitList) return props.children.explicitList;
        if (Array.isArray(props.children)) return props.children;
    }
    return [];
}

function escapeA2Html(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function getIconSvg(name) {
    const icons = {
        'chart': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
        'info': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
        'check': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
        'warning': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    };
    return icons[name] || icons['chart'];
}


// ── A2UI Surface Builder (generates A2UI messages for chart data) ──

/**
 * Build A2UI messages from chart config (backend-compatible bridge).
 * Converts the existing { chart_type, title, labels, data, dataset_label }
 * format into proper A2UI v0.8 messages.
 */
function buildA2UIChartMessages(chartConfig, surfaceId) {
    surfaceId = surfaceId || `chart-${Date.now()}`;

    const messages = [];

    // 1. surfaceUpdate — define the component tree
    messages.push({
        surfaceId,
        surfaceUpdate: {
            components: [
                {
                    id: 'root',
                    component: {
                        Column: {
                            children: { explicitList: ['chart_component'] }
                        }
                    }
                },
                {
                    id: 'chart_component',
                    component: {
                        Chart: {
                            chartType: { literalString: chartConfig.chart_type },
                            title: { literalString: chartConfig.title },
                            labels: chartConfig.labels.map(l => ({ literalString: String(l) })),
                            data: chartConfig.data.map(d => ({ literalNumber: d })),
                            datasetLabel: { literalString: chartConfig.dataset_label },
                        }
                    }
                }
            ]
        }
    });

    // 2. dataModelUpdate — empty for simple charts
    messages.push({
        surfaceId,
        dataModelUpdate: { contents: {} }
    });

    // 3. beginRendering
    messages.push({
        surfaceId,
        beginRendering: { root: 'root' }
    });

    return messages;
}


// ── Render an A2UI Surface into a chat message ──────────────

/**
 * Render A2UI messages array into a DOM element suitable for
 * embedding in the chat. This is the main entry point for the frontend.
 */
function renderA2UISurface(a2uiMessages) {
    const processor = new A2UIMessageProcessor();
    processor.processMessages(a2uiMessages);

    const renderer = new A2UIRenderer(processor);

    const container = document.createElement('div');
    container.className = 'a2ui-surface-container';

    // Render each surface
    for (const [surfaceId] of processor.surfaces) {
        const surfaceEl = renderer.renderSurface(surfaceId);
        if (surfaceEl) {
            const surfaceWrapper = document.createElement('div');
            surfaceWrapper.className = 'a2ui-surface';
            surfaceWrapper.dataset.surfaceId = surfaceId;
            surfaceWrapper.appendChild(surfaceEl);
            container.appendChild(surfaceWrapper);
        }
    }

    return container;
}


// ── Convert legacy chart config to A2UI and render ──────────

/**
 * Takes a legacy chart config { chart_type, title, labels, data, dataset_label }
 * and renders it as an A2UI surface.
 */
function renderA2UIChart(chartConfig) {
    const surfaceId = `chart-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
    const messages = buildA2UIChartMessages(chartConfig, surfaceId);
    return renderA2UISurface(messages);
}


// ── Expose globally ─────────────────────────────────────────
window.A2UI = {
    MessageProcessor: A2UIMessageProcessor,
    Renderer: A2UIRenderer,
    registerComponent: registerA2UIComponent,
    renderSurface: renderA2UISurface,
    renderChart: renderA2UIChart,
    buildChartMessages: buildA2UIChartMessages,
    CATALOG: A2UI_CATALOG,
};
