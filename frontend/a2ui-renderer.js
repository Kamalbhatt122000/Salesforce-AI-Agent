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
// Global chart ID counter — shared across all renderer instances so every
// canvas element gets a unique ID even when multiple renderers are created.
let _globalChartCounter = 0;

class A2UIRenderer {
    constructor(processor) {
        this.processor = processor;
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
            surfaceId,
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
        return `a2ui-chart-${Date.now()}-${++_globalChartCounter}`;
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

/**
 * Robust chart initialisation scheduler.
 * ─────────────────────────────────────
 * The canvas element is created inside a detached DOM fragment.  It only
 * enters the *live document* when the caller appends the returned wrapper
 * to the chat container.
 *
 * KEY FIX: Uses `canvasEl.isConnected` and the direct canvas element
 * reference instead of `document.getElementById()`.  This eliminates
 * the duplicate-ID race condition that caused intermittent blank charts
 * when multiple renderers each produced "a2ui-chart-1".
 *
 * Strategy (three tiers, whichever fires first wins):
 *  1. Immediate check — in case the wrapper was already appended
 *     synchronously before this function runs.
 *  2. MutationObserver — watches `document.body` for child-list /
 *     subtree additions.  Fires the instant the canvas appears in the
 *     DOM, with zero polling overhead.
 *  3. setInterval fallback (50 ms, up to 10 s) — safety net for edge
 *     cases where MutationObserver might miss it (e.g. the element was
 *     added before the observer was connected, between steps 1 and 2).
 */
function _scheduleChartInit(canvasEl, chartId, chartJsConfig) {
    let initialised = false;

    function doInit() {
        if (initialised) return true;
        // Use the direct element reference's `isConnected` property
        // instead of getElementById — immune to duplicate-ID issues.
        if (!canvasEl.isConnected) return false; // Not in DOM yet

        initialised = true;
        try {
            // Pass the actual canvas element directly to Chart.js
            // instead of looking it up by ID.  This guarantees we
            // always initialise on the correct canvas.
            new Chart(canvasEl, chartJsConfig);
            console.log('[A2UI Chart] ✓ Initialised:', chartId);
        } catch (err) {
            console.error('[A2UI Chart] Failed to create chart:', chartId, err);
        }
        return true;
    }

    // ── Tier 1: immediate ──
    if (doInit()) return;

    // ── Tier 2: MutationObserver ──
    let observer = null;
    if (typeof MutationObserver !== 'undefined') {
        observer = new MutationObserver(() => {
            if (canvasEl.isConnected) {
                if (doInit()) {
                    observer.disconnect();
                    observer = null;
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // ── Tier 3: setInterval fallback ──
    let elapsed = 0;
    const INTERVAL = 50;   // ms
    const MAX_WAIT = 10000; // 10 seconds
    const fallback = setInterval(() => {
        elapsed += INTERVAL;
        if (initialised) {
            clearInterval(fallback);
            if (observer) { observer.disconnect(); observer = null; }
            return;
        }
        if (doInit()) {
            clearInterval(fallback);
            if (observer) { observer.disconnect(); observer = null; }
            return;
        }
        if (elapsed >= MAX_WAIT) {
            clearInterval(fallback);
            if (observer) { observer.disconnect(); observer = null; }
            console.error('[A2UI Chart] Canvas never appeared in DOM after 10s:', chartId);
        }
    }, INTERVAL);
}

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

    // ── Chart.js configuration ──
    const chartJsConfig = {
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
    };

    // Robust chart init: waits for canvas to be in the live DOM using
    // MutationObserver + setInterval fallback so it never silently fails.
    _scheduleChartInit(canvas, chartId, chartJsConfig);

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

    const multiChartConfig = {
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
    };

    _scheduleChartInit(canvas, chartId, multiChartConfig);

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


// ── Form Component ──────────────────────────────────────────
registerA2UIComponent('Form', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-form-surface';

    const objectName = context.renderer.resolveValue(props.objectName, context) || 'Record';
    const formTitle = context.renderer.resolveValue(props.title, context) || `Create ${objectName}`;
    const formId = `a2ui-form-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
    el.dataset.formId = formId;
    el.dataset.objectName = objectName;

    // Header
    const header = document.createElement('div');
    header.className = 'a2ui-form-header';
    header.innerHTML = `
        <div class="a2ui-form-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/>
                <line x1="9" y1="15" x2="15" y2="15"/>
            </svg>
        </div>
        <span class="a2ui-form-title">${escapeA2Html(formTitle)}</span>
        <span class="a2ui-chart-badge">A2UI</span>
    `;
    el.appendChild(header);

    // Form body
    const formBody = document.createElement('div');
    formBody.className = 'a2ui-form-body';
    formBody.dataset.formId = formId;

    const children = getChildIds(props);
    for (const childId of children) {
        formBody.appendChild(context.renderer.renderChildById(childId, context));
    }

    el.appendChild(formBody);

    // Status area (for success/error messages)
    const statusArea = document.createElement('div');
    statusArea.className = 'a2ui-form-status';
    statusArea.id = `${formId}-status`;
    el.appendChild(statusArea);

    return el;
});

// ── FormField Component ─────────────────────────────────────
registerA2UIComponent('FormField', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-form-field';

    const label = context.renderer.resolveValue(props.label, context) || '';
    const fieldName = context.renderer.resolveValue(props.fieldName, context) || '';
    const fieldType = context.renderer.resolveValue(props.fieldType, context) || 'text';
    const placeholder = context.renderer.resolveValue(props.placeholder, context) || '';
    const required = props.required === true;
    const options = props.options || [];

    // Label
    const labelEl = document.createElement('label');
    labelEl.className = 'a2ui-form-label';
    labelEl.textContent = label;
    if (required) {
        const req = document.createElement('span');
        req.className = 'a2ui-form-required';
        req.textContent = ' *';
        labelEl.appendChild(req);
    }
    el.appendChild(labelEl);

    // Input
    let inputEl;
    if (fieldType === 'textarea') {
        inputEl = document.createElement('textarea');
        inputEl.className = 'a2ui-form-input a2ui-form-textarea';
        inputEl.rows = 3;
    } else if (fieldType === 'select') {
        inputEl = document.createElement('select');
        inputEl.className = 'a2ui-form-input a2ui-form-select';
        // Add empty option
        const emptyOpt = document.createElement('option');
        emptyOpt.value = '';
        emptyOpt.textContent = placeholder || `Select ${label}...`;
        inputEl.appendChild(emptyOpt);
        // Add options
        const resolvedOptions = Array.isArray(options) ? options : [];
        for (const opt of resolvedOptions) {
            const optEl = document.createElement('option');
            const optVal = context.renderer.resolveValue(opt, context);
            optEl.value = optVal;
            optEl.textContent = optVal;
            inputEl.appendChild(optEl);
        }
    } else {
        inputEl = document.createElement('input');
        inputEl.className = 'a2ui-form-input';
        inputEl.type = fieldType;
    }

    inputEl.name = fieldName;
    inputEl.placeholder = placeholder;
    inputEl.dataset.fieldName = fieldName;
    if (required) inputEl.required = true;

    // Validation feedback on blur
    inputEl.addEventListener('blur', () => {
        if (required && !inputEl.value.trim()) {
            inputEl.classList.add('a2ui-form-error');
        } else {
            inputEl.classList.remove('a2ui-form-error');
        }
    });
    inputEl.addEventListener('input', () => {
        inputEl.classList.remove('a2ui-form-error');
    });

    el.appendChild(inputEl);
    return el;
});

// ── FormButton Component ────────────────────────────────────
registerA2UIComponent('FormButton', (props, context) => {
    const el = document.createElement('div');
    el.className = 'a2ui-form-actions';

    const label = context.renderer.resolveValue(props.label, context) || 'Create Record';
    const objectName = context.renderer.resolveValue(props.objectName, context) || '';

    const btn = document.createElement('button');
    btn.className = 'a2ui-form-submit-btn';
    btn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>${escapeA2Html(label)}</span>
    `;

    btn.addEventListener('click', async () => {
        // Find the parent form surface
        const formSurface = btn.closest('.a2ui-form-surface');
        if (!formSurface) return;

        const formBody = formSurface.querySelector('.a2ui-form-body');
        const statusArea = formSurface.querySelector('.a2ui-form-status');
        const objName = formSurface.dataset.objectName || objectName;

        // Collect field values
        const inputs = formBody.querySelectorAll('[data-field-name]');
        const fieldValues = {};
        let hasError = false;

        inputs.forEach(input => {
            const name = input.dataset.fieldName;
            const value = input.value.trim();
            if (input.required && !value) {
                input.classList.add('a2ui-form-error');
                hasError = true;
            }
            if (value) {
                fieldValues[name] = value;
            }
        });

        if (hasError) {
            statusArea.innerHTML = `<div class="a2ui-form-msg a2ui-form-msg-error">Please fill in all required fields.</div>`;
            return;
        }

        // Disable button and show loading
        btn.disabled = true;
        btn.classList.add('a2ui-form-loading');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = `
            <div class="a2ui-form-spinner"></div>
            <span>Creating...</span>
        `;
        statusArea.innerHTML = '';

        try {
            const res = await fetch('/api/create-record-form', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ object_name: objName, field_values: fieldValues }),
            });
            const data = await res.json();

            if (data.success) {
                // Show success
                statusArea.innerHTML = `
                    <div class="a2ui-form-msg a2ui-form-msg-success">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                        <div>
                            <strong>${escapeA2Html(objName)} created successfully!</strong>
                            <div class="a2ui-form-record-id">Record ID: ${escapeA2Html(data.id)}</div>
                        </div>
                    </div>
                `;
                // Disable all inputs
                inputs.forEach(input => { input.disabled = true; input.classList.add('a2ui-form-disabled'); });
                btn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="20 6 9 17 4 12"/>
                    </svg>
                    <span>Created ✓</span>
                `;
                btn.classList.remove('a2ui-form-loading');
                btn.classList.add('a2ui-form-success');
            } else {
                statusArea.innerHTML = `<div class="a2ui-form-msg a2ui-form-msg-error">${escapeA2Html(data.error || 'Failed to create record.')}</div>`;
                btn.innerHTML = originalHTML;
                btn.disabled = false;
                btn.classList.remove('a2ui-form-loading');
            }
        } catch (err) {
            statusArea.innerHTML = `<div class="a2ui-form-msg a2ui-form-msg-error">Network error. Please try again.</div>`;
            btn.innerHTML = originalHTML;
            btn.disabled = false;
            btn.classList.remove('a2ui-form-loading');
        }
    });

    el.appendChild(btn);
    return el;
});


// ── FORM COMPONENTS ─────────────────────────────────────────
// Interactive form components for creating/editing Salesforce records.
// Form state is managed per-surface so multiple forms can coexist.

const _a2uiFormState = new Map();

function _setFormValue(surfaceId, path, value) {
    if (!_a2uiFormState.has(surfaceId)) _a2uiFormState.set(surfaceId, {});
    const state = _a2uiFormState.get(surfaceId);
    const parts = path.replace(/^\//, '').split('/');
    let obj = state;
    for (let i = 0; i < parts.length - 1; i++) {
        if (!obj[parts[i]] || typeof obj[parts[i]] !== 'object') obj[parts[i]] = {};
        obj = obj[parts[i]];
    }
    obj[parts[parts.length - 1]] = value;
}

function _getFormState(surfaceId) {
    return _a2uiFormState.get(surfaceId) || {};
}

// ── TextField ──
registerA2UIComponent('TextField', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-form-field';

    const label = context.renderer.resolveValue(props.label, context) || '';
    const path = props.path || '';
    const required = props.required === true;
    const placeholder = context.renderer.resolveValue(props.placeholder, context) || '';
    const inputType = props.inputType || 'text';
    const surfaceId = context.surfaceId || 'default';

    const labelEl = document.createElement('label');
    labelEl.className = 'a2ui-form-label';
    labelEl.innerHTML = `${escapeA2Html(label)}${required ? '<span class="a2ui-required">*</span>' : ''}`;
    wrapper.appendChild(labelEl);

    const input = document.createElement('input');
    input.type = inputType;
    input.className = 'a2ui-form-input';
    input.placeholder = placeholder;
    input.dataset.path = path;
    if (required) input.required = true;

    // Pre-populate with initial value if available (for update forms)
    const initialValues = (context.dataModel && context.dataModel._initialValues) || {};
    if (initialValues[path] !== undefined && initialValues[path] !== null) {
        input.value = String(initialValues[path]);
        _setFormValue(surfaceId, path, input.value);
    }

    input.addEventListener('input', () => {
        _setFormValue(surfaceId, path, input.value);
        input.classList.remove('a2ui-field-error');
    });
    input.addEventListener('focus', () => input.classList.add('a2ui-field-focus'));
    input.addEventListener('blur', () => input.classList.remove('a2ui-field-focus'));

    wrapper.appendChild(input);
    return wrapper;
});

// ── DropDown ──
registerA2UIComponent('DropDown', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-form-field';

    const label = context.renderer.resolveValue(props.label, context) || '';
    const path = props.path || '';
    const options = props.options || [];
    const required = props.required === true;
    const surfaceId = context.surfaceId || 'default';

    const labelEl = document.createElement('label');
    labelEl.className = 'a2ui-form-label';
    labelEl.innerHTML = `${escapeA2Html(label)}${required ? '<span class="a2ui-required">*</span>' : ''}`;
    wrapper.appendChild(labelEl);

    const select = document.createElement('select');
    select.className = 'a2ui-form-select';
    select.dataset.path = path;

    // Add placeholder option
    const placeholderOpt = document.createElement('option');
    placeholderOpt.value = '';
    placeholderOpt.textContent = `Select ${label}...`;
    placeholderOpt.disabled = true;
    placeholderOpt.selected = true;
    select.appendChild(placeholderOpt);

    // Resolve options — can be literal strings or bound values
    const resolvedOptions = options.map(o => {
        if (typeof o === 'string') return o;
        return context.renderer.resolveValue(o, context) || '';
    });

    resolvedOptions.forEach(opt => {
        const optionEl = document.createElement('option');
        optionEl.value = opt;
        optionEl.textContent = opt;
        select.appendChild(optionEl);
    });

    // Pre-populate with initial value if available (for update forms)
    const initialValues = (context.dataModel && context.dataModel._initialValues) || {};
    if (initialValues[path] !== undefined && initialValues[path] !== null) {
        select.value = String(initialValues[path]);
        _setFormValue(surfaceId, path, select.value);
    }

    select.addEventListener('change', () => {
        _setFormValue(surfaceId, path, select.value);
        select.classList.remove('a2ui-field-error');
    });

    wrapper.appendChild(select);
    return wrapper;
});

// ── DateTimeInput ──
registerA2UIComponent('DateTimeInput', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-form-field';

    const label = context.renderer.resolveValue(props.label, context) || '';
    const path = props.path || '';
    const required = props.required === true;
    const surfaceId = context.surfaceId || 'default';

    const labelEl = document.createElement('label');
    labelEl.className = 'a2ui-form-label';
    labelEl.innerHTML = `${escapeA2Html(label)}${required ? '<span class="a2ui-required">*</span>' : ''}`;
    wrapper.appendChild(labelEl);

    const input = document.createElement('input');
    input.type = 'date';
    input.className = 'a2ui-form-input a2ui-form-date';
    input.dataset.path = path;
    if (required) input.required = true;

    // Pre-populate with initial value if available (for update forms)
    const initialValues = (context.dataModel && context.dataModel._initialValues) || {};
    if (initialValues[path] !== undefined && initialValues[path] !== null) {
        input.value = String(initialValues[path]);
        _setFormValue(surfaceId, path, input.value);
    }

    input.addEventListener('change', () => {
        _setFormValue(surfaceId, path, input.value);
        input.classList.remove('a2ui-field-error');
    });

    wrapper.appendChild(input);
    return wrapper;
});

// ── RadioGroup ──
registerA2UIComponent('RadioGroup', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-form-field';

    const label = context.renderer.resolveValue(props.label, context) || '';
    const path = props.path || '';
    const options = props.options || [];
    const surfaceId = context.surfaceId || 'default';
    const groupName = `radio-${surfaceId}-${path}`.replace(/[^a-zA-Z0-9]/g, '-');

    const labelEl = document.createElement('label');
    labelEl.className = 'a2ui-form-label';
    labelEl.textContent = label;
    wrapper.appendChild(labelEl);

    const radioGroup = document.createElement('div');
    radioGroup.className = 'a2ui-radio-group';

    const resolvedOptions = options.map(o => {
        if (typeof o === 'string') return o;
        return context.renderer.resolveValue(o, context) || '';
    });

    // Pre-populate with initial value if available (for update forms)
    const initialValues = (context.dataModel && context.dataModel._initialValues) || {};
    const initialVal = initialValues[path];

    resolvedOptions.forEach((opt, i) => {
        const radioWrapper = document.createElement('label');
        radioWrapper.className = 'a2ui-radio-option';

        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = groupName;
        radio.value = opt;
        radio.className = 'a2ui-radio-input';

        // Check if this is the initial value
        if (initialVal !== undefined && String(initialVal) === opt) {
            radio.checked = true;
            radioWrapper.classList.add('selected');
            _setFormValue(surfaceId, path, opt);
        }

        radio.addEventListener('change', () => {
            _setFormValue(surfaceId, path, opt);
            radioGroup.querySelectorAll('.a2ui-radio-option').forEach(r => r.classList.remove('selected'));
            radioWrapper.classList.add('selected');
        });

        const span = document.createElement('span');
        span.className = 'a2ui-radio-label';
        span.textContent = opt;

        radioWrapper.appendChild(radio);
        radioWrapper.appendChild(span);
        radioGroup.appendChild(radioWrapper);
    });

    wrapper.appendChild(radioGroup);
    return wrapper;
});

// ── Button (with form submission) ──
registerA2UIComponent('Button', (props, context) => {
    const btn = document.createElement('button');
    btn.className = 'a2ui-form-button';

    const label = context.renderer.resolveValue(props.label, context) || 'Submit';
    const surfaceId = context.surfaceId || 'default';
    const action = props.action || {};
    const actionName = action.name || '';

    btn.innerHTML = `
        <span class="a2ui-btn-text">${escapeA2Html(label)}</span>
        <span class="a2ui-btn-loader" style="display:none;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
            </svg>
        </span>
    `;

    btn.addEventListener('click', async () => {
        // Get form config from dataModel
        const formConfig = context.dataModel._formConfig || {};
        const objectName = formConfig.objectName || '';
        const fieldMapping = formConfig.fieldMapping || {};
        const requiredPaths = formConfig.requiredFields || [];
        const formMode = formConfig.mode || 'create';
        const recordId = formConfig.recordId || '';

        // Get form state
        const formState = _getFormState(surfaceId);

        // Validate required fields
        let hasErrors = false;
        const surfaceEl = btn.closest('.a2ui-surface') || btn.closest('.a2ui-surface-container');

        requiredPaths.forEach(reqPath => {
            const parts = reqPath.replace(/^\//, '').split('/');
            let val = formState;
            for (const p of parts) { val = val ? val[p] : undefined; }
            if (!val || !String(val).trim()) {
                hasErrors = true;
                if (surfaceEl) {
                    const input = surfaceEl.querySelector(`[data-path="${reqPath}"]`);
                    if (input) input.classList.add('a2ui-field-error');
                }
            }
        });

        if (hasErrors) {
            _showFormMessage(btn, 'Please fill in all required fields.', 'error');
            return;
        }

        // Map form paths to Salesforce field names
        const sfFieldValues = {};
        for (const [path, sfField] of Object.entries(fieldMapping)) {
            const parts = path.replace(/^\//, '').split('/');
            let val = formState;
            for (const p of parts) { val = val ? val[p] : undefined; }
            if (val !== undefined && val !== null && String(val).trim()) {
                sfFieldValues[sfField] = val;
            }
        }

        // Show loading state
        btn.disabled = true;
        btn.classList.add('a2ui-btn-loading');
        btn.querySelector('.a2ui-btn-text').style.display = 'none';
        btn.querySelector('.a2ui-btn-loader').style.display = 'inline-flex';

        // Build request body — include record_id for update mode
        const requestBody = {
            object_name: objectName,
            field_values: sfFieldValues,
            action: actionName,
        };
        if (formMode === 'update' && recordId) {
            requestBody.record_id = recordId;
        }

        try {
            const res = await fetch('/api/form-submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            const data = await res.json();

            if (data.success) {
                btn.classList.remove('a2ui-btn-loading');
                btn.classList.add('a2ui-btn-success');
                btn.querySelector('.a2ui-btn-text').style.display = 'inline';
                const successLabel = formMode === 'update' ? '✓ Updated!' : '✓ Created!';
                btn.querySelector('.a2ui-btn-text').textContent = successLabel;
                btn.querySelector('.a2ui-btn-loader').style.display = 'none';
                const successMsg = formMode === 'update'
                    ? `${objectName} updated successfully! (ID: ${data.id || recordId})`
                    : `${objectName} created successfully! (ID: ${data.id})`;
                _showFormMessage(btn, successMsg, 'success');

                // Disable all form inputs
                if (surfaceEl) {
                    surfaceEl.querySelectorAll('input, select').forEach(el => el.disabled = true);
                }
            } else {
                btn.disabled = false;
                btn.classList.remove('a2ui-btn-loading');
                btn.querySelector('.a2ui-btn-text').style.display = 'inline';
                btn.querySelector('.a2ui-btn-text').textContent = label;
                btn.querySelector('.a2ui-btn-loader').style.display = 'none';
                _showFormMessage(btn, data.error || 'Operation failed.', 'error');
            }
        } catch (err) {
            btn.disabled = false;
            btn.classList.remove('a2ui-btn-loading');
            btn.querySelector('.a2ui-btn-text').style.display = 'inline';
            btn.querySelector('.a2ui-btn-text').textContent = label;
            btn.querySelector('.a2ui-btn-loader').style.display = 'none';
            _showFormMessage(btn, 'Network error. Please try again.', 'error');
        }
    });

    return btn;
});

function _showFormMessage(btnEl, message, type) {
    // Remove existing message
    const existing = btnEl.parentElement.querySelector('.a2ui-form-message');
    if (existing) existing.remove();

    const msgEl = document.createElement('div');
    msgEl.className = `a2ui-form-message a2ui-form-message-${type}`;
    msgEl.textContent = message;
    btnEl.parentElement.insertBefore(msgEl, btnEl.nextSibling);

    // Auto-remove error messages after 5s
    if (type === 'error') {
        setTimeout(() => msgEl.remove(), 5000);
    }
}


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


// ── CUSTOM: ReportTable Component ───────────────────────────
// Renders report data as a premium interactive table with filters,
// grouping, aggregates, and a link to the Salesforce report.

registerA2UIComponent('ReportTable', (props, context) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'a2ui-report-surface';

    const title = context.renderer.resolveValue(props.title, context) || 'Report';
    const format = context.renderer.resolveValue(props.format, context) || 'TABULAR';
    const reportUrl = context.renderer.resolveValue(props.reportUrl, context) || '';
    const totalRows = context.renderer.resolveValue(props.totalRows, context) || 0;
    const columns = props.columns || [];
    const rows = props.rows || [];
    const filters = props.filters || [];
    const aggregates = props.aggregates || {};

    // ── Header ──
    const header = document.createElement('div');
    header.className = 'a2ui-report-header';
    const formatClass = format.toLowerCase().replace(/_/g, '');
    header.innerHTML = `
        <div class="a2ui-report-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
        </div>
        <span class="a2ui-report-title">${escapeA2Html(title)}</span>
        <span class="a2ui-report-format-badge ${formatClass}">${escapeA2Html(format)}</span>
        <span class="a2ui-chart-badge">A2UI</span>
    `;
    wrapper.appendChild(header);

    // ── Filters ──
    if (filters.length > 0) {
        const filtersDiv = document.createElement('div');
        filtersDiv.className = 'a2ui-report-filters';
        filters.forEach(f => {
            const chip = document.createElement('span');
            chip.className = 'a2ui-report-filter-chip';
            const col = context.renderer.resolveValue(f.column, context) || '';
            const op = context.renderer.resolveValue(f.operator, context) || '=';
            const val = context.renderer.resolveValue(f.value, context) || '';
            chip.innerHTML = `<span class="filter-key">${escapeA2Html(col)}</span> ${escapeA2Html(op)} ${escapeA2Html(val)}`;
            filtersDiv.appendChild(chip);
        });
        wrapper.appendChild(filtersDiv);
    }

    // ── Table ──
    if (columns.length > 0 && rows.length > 0) {
        const tableWrapper = document.createElement('div');
        tableWrapper.className = 'a2ui-report-table-wrapper';

        const table = document.createElement('table');
        table.className = 'a2ui-report-table';

        // Resolve column labels
        const colLabels = columns.map(c =>
            context.renderer.resolveValue(c.label || c, context) || ''
        );

        // Thead
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        colLabels.forEach(label => {
            const th = document.createElement('th');
            th.textContent = label;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Tbody
        const tbody = document.createElement('tbody');
        let lastGroup = null;

        rows.forEach(row => {
            // Handle group rows for SUMMARY reports
            const rowData = (typeof row === 'object' && !Array.isArray(row))
                ? row : {};
            const group = rowData._group;

            if (group && group !== lastGroup) {
                const groupTr = document.createElement('tr');
                groupTr.className = 'a2ui-report-group-row';
                const groupTd = document.createElement('td');
                groupTd.colSpan = colLabels.length;
                groupTd.textContent = `▸ ${group}`;
                groupTr.appendChild(groupTd);
                tbody.appendChild(groupTr);
                lastGroup = group;
            }

            const tr = document.createElement('tr');
            colLabels.forEach(label => {
                const td = document.createElement('td');
                td.textContent = rowData[label] || '';
                td.title = rowData[label] || '';
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        // Aggregate row
        const aggKeys = Object.keys(aggregates).filter(k => !k.startsWith('_'));
        if (aggKeys.length > 0) {
            const totalTr = document.createElement('tr');
            totalTr.className = 'a2ui-report-total-row';
            colLabels.forEach((label, i) => {
                const td = document.createElement('td');
                if (i === 0) {
                    td.textContent = 'Total';
                } else {
                    const aggVal = aggregates[label];
                    td.textContent = aggVal !== undefined ? String(aggVal) : '';
                }
                totalTr.appendChild(td);
            });
            tbody.appendChild(totalTr);
        }

        table.appendChild(tbody);
        tableWrapper.appendChild(table);
        wrapper.appendChild(tableWrapper);
    }

    // ── Meta Footer ──
    const meta = document.createElement('div');
    meta.className = 'a2ui-report-meta';
    meta.innerHTML = `
        <span class="a2ui-report-meta-text">
            <span class="a2ui-report-count-badge">${escapeA2Html(String(totalRows))} rows</span>
        </span>
        ${reportUrl ? `<a class="a2ui-report-meta-link" href="${escapeA2Html(reportUrl)}" target="_blank" rel="noopener">Open in Salesforce ↗</a>` : ''}
    `;
    wrapper.appendChild(meta);

    return wrapper;
});


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
