class Colorscale {
    constructor(p, colorInvalid=[0,0,0,255], colorLow=undefined, colorHigh=undefined) {
        this.colorInvalid = colorInvalid;
        this.colorLow = colorLow;
        this.colorHight = colorHigh;
        this.resamplePalette(p, 256);
    }

    rgba(v) {
        if ((v == undefined) || isNaN(v)) {
            return this.colorInvalid;
        }
        if (v < this.a){
            return this.colorLow;
        }
        if (v > this.b){
            return this.colorHigh;
        }

        let i = (v - this.a) / (this.b - this.a) * (this.n - 1);
        i = Math.round(i);
        i = Math.max(0, Math.min(this.n - 1, i));
        return this.rgba_sampled[i];
    }

    rgba_css(v) {
        const color = this.rgba(v);
        return "rgba(" + [color[0], color[1], color[2], color[3]].join(',') + ")";
    }

    rgb_css(v) {
        const color = this.rgba(v);
        return "rgb(" + [color[0], color[1], color[2]].join(',') + ")";
    }

    rgb_hex(v) {
        const  color = this.rgba(v);
        return "#" + this.hex2digits(color[0]) + this.hex2digits(color[1]) + this.hex2digits(color[2]);
    }

    hex2digits(v) {
        const hex = v.toString(16);
        return hex.length == 1 ? "0" + hex : hex;
    }

    samplePalette(x, v, xi) {
        const n = x.length;
        let y;

        let  ia = 0;
        let ib = n - 1;

        while (ib - ia > 1) {
            const ic = Math.round(0.5 * (ia + ib));
            if (xi < x[ic]) {
                ib = ic;
            } else {
                ia = ic;
            }
        }

        const xa = x[ia];
        const xb = x[ib];
        const alpha = (xi - xa) / (xb - xa);

        y = this.interpolateColorLinear(v[ia], v[ib], alpha);
        
        return y;
    }

    interpolateColorLinear(xa, xb, alpha) {
        let m = xa.length;
        let y = Array(m);
        for (let i = 0; i < m; i++) {
            y[i] = Math.round(xa[i] * (1 - alpha) + xb[i] * alpha);
        }
        return y;
    }

    ensureRgba(c){
        switch (c.length){
            case 1:
                return Array(c, c, c, 255);
            case 3:
                return c.concat(255);
            case 4:
                return c;
        }
    }

    resamplePalette(C, n) {
        // sort palette definition by x
        C = C.sort(function (a, b) {
            return a[0] - b[0];
        });

        // split into position and color
        const x = C.map(c => c[0]);
        let v = C.map(c => this.ensureRgba(c[1]));

        // determine length, min and max
        this.a = Math.min(...x);
        this.b = Math.max(...x);
        this.n = n;

        // default  colors used if sampled outside definition range
        if (!this.colorLow){
            this.colorLow= v[0];
        }
        if (!this.colorHigh){
            this.colorHigh = v[v.length-1];
        }

        const p = new Array(n);
        for (let i = 0; i < n; i++) {
            const xi = this.a + (i / (n - 1)) * (this.b - this.a);
            p[i] = this.samplePalette(x, v, xi);
        }

        this.rgba_sampled = p;
    }

    writeLegend(target, ticks, postfix) {
        var div = document.getElementById(target);
        var canvas = document.createElement("canvas");
        var context = canvas.getContext("2d");

        var barWidth = this.n;
        var barLeft = 25;
        var barHeight = 25;

        canvas.width = 300;
        canvas.height = 50;

        var imgData = context.getImageData(0, 0, barWidth, barHeight);
        var data = imgData.data;

        var k = 0;
        for (var y = 0; y < barHeight; y++) {
            for (var x = 0; x < barWidth; x++) {
                for (var c = 0; c < 4; c++) {
                    data[k] = this.rgba_sampled[x][c];
                    k += 1;
                }
            }
        }
        context.putImageData(imgData, barLeft, 0);

        context.font = "12px Arial";
        context.textAlign = "center";
        context.textBaseline = "top";
        for (var i = 0; i < ticks.length; i++) {
            var v = ticks[i];
            var x = barLeft + (v - this.a) / (this.b - this.a) * (this.n - 1);
            var y = 25;
            context.fillText(v.toFixed(2) + postfix, x, y);
        }

        var image = new Image();
        image.src = canvas.toDataURL();
        image.height = canvas.height;
        image.width = canvas.width;
        div.appendChild(image);

    }
}

colorscaleUrban = new Colorscale([
    [0.0000, [ 64,   0,   0]],
    [1.4999, [196,   0,   0]],
    [1.5000, [196, 196,   0]],
    [2.0000, [  0, 196,   0]],
    [2.5500, [  0, 255,   0]]
], [128, 128, 128]);

colorscaleRural = new Colorscale([
    [0.0000, [ 64,   0,   0]],
    [1.9999, [196,   0,   0]],
    [2.0000, [196, 196,   0]],
    [2.5000, [  0, 196,   0]],
    [2.5500, [  0, 255,   0]]
], [128, 128, 128]);	