// ===== Simple Chart Library =====
var SimpleChart = (function() {
    function Chart(canvasId, options) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.type = options.type || 'bar';
        this.data = options.data || [];
        this.labels = options.labels || [];
        this.colors = options.colors || ['#007AFF', '#34C759', '#FF9500', '#AF52DE', '#5AC8FA', '#FF2D55'];
        this.maxY = options.maxY || null;
        this.resize();
        this._resizeHandler = this.resize.bind(this);
        window.addEventListener('resize', this._resizeHandler);
    }

    Chart.prototype.resize = function() {
        var rect = this.canvas.parentElement.getBoundingClientRect();
        var dpr = window.devicePixelRatio || 1;
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.setTransform(1, 0, 0, 1, 0, 0);
        this.ctx.scale(dpr, dpr);
        this.w = rect.width;
        this.h = rect.height;
        this.draw();
    };

    Chart.prototype.destroy = function() {
        window.removeEventListener('resize', this._resizeHandler);
    };

    Chart.prototype.draw = function() {
        if (!this.data.length) return;
        if (this.type === 'bar') this._drawBars();
        else if (this.type === 'line') this._drawLine();
        else if (this.type === 'donut') this._drawDonut();
    };

    Chart.prototype.update = function(data, labels, colors) {
        this.data = data; this.labels = labels;
        if (colors) this.colors = colors;
        this.draw();
    };

    Chart.prototype._drawBars = function() {
        var ctx = this.ctx, w = this.w, h = this.h;
        var pad = {top: 10, right: 10, bottom: 32, left: 42};
        var cw = w - pad.left - pad.right;
        var ch = h - pad.top - pad.bottom;
        var maxVal = this.maxY || Math.max.apply(null, this.data) * 1.2 || 1;

        ctx.clearRect(0, 0, w, h);

        // Grid lines
        var gridLines = 4;
        ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--border').trim() || 'rgba(0,0,0,0.06)';
        ctx.lineWidth = 1;
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#86868b';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'right';
        for (var i = 0; i <= gridLines; i++) {
            var y = pad.top + (ch / gridLines) * i;
            var val = maxVal - (maxVal / gridLines) * i;
            ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
            ctx.fillText(Math.round(val), pad.left - 8, y + 4);
        }

        // Bars
        var barGap = cw * 0.15;
        var barW = (cw - barGap) / this.data.length - barGap / this.data.length;
        if (barW > 60) barW = 60;

        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        for (var j = 0; j < this.data.length; j++) {
            var x = pad.left + barGap / 2 + (cw / this.data.length) * j + (cw / this.data.length - barW) / 2;
            var barH = (this.data[j] / maxVal) * ch;
            var by = pad.top + ch - barH;
            var color = this.colors[j % this.colors.length];

            // Gradient
            var grad = ctx.createLinearGradient(x, by, x, pad.top + ch);
            grad.addColorStop(0, color); grad.addColorStop(1, color + (isDark ? '44' : '22'));
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.roundRect(x, by, barW, barH, [4, 4, 0, 0]);
            ctx.fill();

            // Value
            ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#1d1d1f';
            ctx.font = 'bold 11px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(this.data[j], x + barW / 2, by - 6);

            // Label
            ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#86868b';
            ctx.font = '10px -apple-system, sans-serif';
            ctx.fillText(this.labels[j] || '', x + barW / 2, pad.top + ch + 16);
        }
    };

    Chart.prototype._drawLine = function() {
        var ctx = this.ctx, w = this.w, h = this.h;
        var pad = {top: 16, right: 16, bottom: 32, left: 42};
        var cw = w - pad.left - pad.right;
        var ch = h - pad.top - pad.bottom;
        var maxVal = this.maxY || Math.max.apply(null, this.data) * 1.2 || 1;

        ctx.clearRect(0, 0, w, h);

        // Grid
        var gridLines = 4;
        ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--border').trim() || 'rgba(0,0,0,0.06)';
        ctx.lineWidth = 1;
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#86868b';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'right';
        for (var i = 0; i <= gridLines; i++) {
            var y = pad.top + (ch / gridLines) * i;
            var val = maxVal - (maxVal / gridLines) * i;
            ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
            ctx.fillText(Math.round(val), pad.left - 8, y + 4);
        }

        if (this.data.length < 2) return;

        // Area fill
        var grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + ch);
        grad.addColorStop(0, 'rgba(0,122,255,0.15)'); grad.addColorStop(1, 'rgba(0,122,255,0.0)');
        ctx.fillStyle = grad;
        ctx.beginPath();
        var x0 = pad.left;
        ctx.moveTo(x0, pad.top + ch);
        for (var k = 0; k < this.data.length; k++) {
            var px = pad.left + (cw / (this.data.length - 1 || 1)) * k;
            var py = pad.top + ch - (this.data[k] / maxVal) * ch;
            ctx.lineTo(px, py);
        }
        ctx.lineTo(pad.left + cw, pad.top + ch);
        ctx.closePath(); ctx.fill();

        // Line
        ctx.strokeStyle = this.colors[0];
        ctx.lineWidth = 2.5;
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        ctx.beginPath();
        for (var m = 0; m < this.data.length; m++) {
            var lx = pad.left + (cw / (this.data.length - 1 || 1)) * m;
            var ly = pad.top + ch - (this.data[m] / maxVal) * ch;
            if (m === 0) ctx.moveTo(lx, ly); else ctx.lineTo(lx, ly);
        }
        ctx.stroke();

        // Dots
        for (var n = 0; n < this.data.length; n++) {
            var dx = pad.left + (cw / (this.data.length - 1 || 1)) * n;
            var dy = pad.top + ch - (this.data[n] / maxVal) * ch;
            ctx.fillStyle = '#fff';
            ctx.beginPath(); ctx.arc(dx, dy, 5, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = this.colors[0];
            ctx.beginPath(); ctx.arc(dx, dy, 3.5, 0, Math.PI * 2); ctx.fill();
            ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#86868b';
            ctx.font = '10px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(this.labels[n] || '', dx, pad.top + ch + 16);
        }
    };

    Chart.prototype._drawDonut = function() {
        var ctx = this.ctx, w = this.w, h = this.h;
        var cx = w / 2, cy = h / 2;
        var outerR = Math.min(cx, cy) - 10;
        var innerR = outerR * 0.6;
        var total = this.data.reduce(function(a, b) { return a + b; }, 0) || 1;

        ctx.clearRect(0, 0, w, h);

        var startAngle = -Math.PI / 2;
        for (var i = 0; i < this.data.length; i++) {
            var slice = (this.data[i] / total) * Math.PI * 2;
            ctx.fillStyle = this.colors[i % this.colors.length];
            ctx.beginPath();
            ctx.arc(cx, cy, outerR, startAngle, startAngle + slice);
            ctx.arc(cx, cy, innerR, startAngle + slice, startAngle, true);
            ctx.closePath(); ctx.fill();
            startAngle += slice;
        }

        // Center text
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#1d1d1f';
        ctx.font = 'bold 22px -apple-system, sans-serif';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(total + 'h', cx, cy - 6);
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim() || '#86868b';
        ctx.font = '12px -apple-system, sans-serif';
        ctx.fillText('总工时', cx, cy + 14);
    };

    return Chart;
})();
