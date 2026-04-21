/**
 * Плагин для отрисовки лимитов (MAX/MIN)
 */
const limitLinesPlugin = {
    id: 'limitLines',
    afterDraw: (chart) => {
        const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = chart;
        const limits = chart.config.options.customLimits;
        if (!limits) return;

        const drawLine = (val, color, label) => {
            if (val === undefined || val === null) return;
            const yPos = y.getPixelForValue(val);
            if (yPos < top || yPos > bottom) return;

            ctx.save();
            ctx.strokeStyle = color;
            ctx.setLineDash([5, 5]);
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(left, yPos);
            ctx.lineTo(right, yPos);
            ctx.stroke();
            ctx.fillStyle = color;
            ctx.font = "bold 10px Arial";
            ctx.fillText(label + ": " + val, left + 5, yPos - 5);
            ctx.restore();
        };

        drawLine(limits.max, '#dc3545', 'MAX');
        drawLine(limits.min, '#007bff', 'MIN');
    }
};