class FeatureStyle{
	constructor(){
		this.defaultStyle = new ol.style.Style({
			stroke: new ol.style.Stroke({
				color: [0, 0, 0, 255],
				width: 2,
			})
		});
	}

	select(){
	}

	deselect(){
	}

	styleFunction(feature, resolution, selected=false, hovered=false){
		return this.defaultStyle;
	}


	resolutionToNearMidFar(resolution){
        const near = this.smoothStep(resolution, 2.0, 1.0);
		const mid = this.smoothStep(resolution, 30.0, 20.0) - this.smoothStep(resolution, 2.0, 1.0);
	    const far = this.smoothStep(resolution, 20.0, 30.0);

        return Array(near, mid, far);
    }
	    
    smoothStep(x, a, b) {
        const y = (x - a) / (b - a);
        return Math.max(0.0, Math.min(1.0, y));
    }
}


class RoadStyle_RatioCloseOvertakers extends FeatureStyle{

	constructor(){
		super();
		this.palette = new Colorscale([
			[0, [0, 255, 0]],
			[50.0, [255, 255, 0]],
			[100.0, [255, 0, 0]]],
			[128, 128, 128, 255]);
	}

	styleFunction(feature, resolution, selected=false, hovered=false){
		const valid = feature.get('valid');

		const n = feature.get('distance_overtaker_n');
		const a = feature.get('distance_overtaker_n_below_limit');
		let p = undefined;
		if (n > 0) {
			p = 100.0 * a / n;
		}
   		let color = this.palette.rgba(p);

		const w = this.resolutionToNearMidFar(resolution);

		const alpha = 1.0 * w[0] + 0.5 * w[1] + 0.5 * w[2];
		const width = ((selected|hovered) ? 4.0 : 2.0) * w[0] + 4 * w[1] + 200.0 / resolution * w[2];

		color[3] = alpha;

		const style = new ol.style.Style({
			stroke: new ol.style.Stroke({
				color: color,
				width: width,
			})
		});
		return style;
	}

}



class RoadStyle_MeanDistance extends FeatureStyle{
	constructor(){
		super();
		this.colorInvalid = [0, 0, 0, 255];

		this.colorscaleUrban = new Colorscale([
			[0.0000, [ 64,   0,   0]],
			[1.4999, [196,   0,   0]],
			[1.5000, [196, 196,   0]],
			[2.0000, [  0, 196,   0]],
			[2.5500, [  0, 255,   0]]
		], [128, 128, 128]);
		
		this.colorscaleRural = new Colorscale([
			[0.0000, [ 64,   0,   0]],
			[1.9999, [196,   0,   0]],
			[2.0000, [196, 196,   0]],
			[2.5000, [  0, 196,   0]],
			[2.5500, [  0, 255,   0]]
		], [128, 128, 128]);	
	}

	styleFunction(feature, resolution, selected=false, hovered=false){
		const valid = feature.get('valid');

		let color;
		if (valid){
			const zone = feature.get('zone');
			let palette;
			switch (zone){
				case "urban":
				palette = this.colorscaleUrban;
				break;
				case "rural":
				palette= this.colorscaleRural;
				break;
				default:
				palette = this.colorscaleUrban;
			}
			const d = feature.get('distance_overtaker_mean');
			color = palette.rgba(d)	
		} else {
			color = this.colorInvalid;
		}

		const w = this.resolutionToNearMidFar(resolution);

		const alpha = 1.0 * w[0] + 0.5 * w[1] + 0.5 * w[2];
		const width = ((selected|hovered) ? 4.0 : 2.0) * w[0] + 4 * w[1] + 200.0 / resolution * w[2];

		color[3] = alpha;

		const style = new ol.style.Style({
			stroke: new ol.style.Stroke({
				color: color,
				width: width,
			})
		});
		return style;
	}

}

class RoadStyle_MedianDistance extends FeatureStyle{
	constructor(){
		super();
		this.colorInvalid = [0, 0, 0, 255];

		this.colorscaleUrban = new Colorscale([
			[0.0000, [ 64,   0,   0]],
			[1.4999, [196,   0,   0]],
			[1.5000, [196, 196,   0]],
			[2.0000, [  0, 196,   0]],
			[2.5500, [  0, 255,   0]]
		], [128, 128, 128]);
		
		this.colorscaleRural = new Colorscale([
			[0.0000, [ 64,   0,   0]],
			[1.9999, [196,   0,   0]],
			[2.0000, [196, 196,   0]],
			[2.5000, [  0, 196,   0]],
			[2.5500, [  0, 255,   0]]
		], [128, 128, 128]);	
	}

	styleFunction(feature, resolution, selected=false, hovered=false){
		const valid = feature.get('valid');

		let color;
		if (valid){
			const zone = feature.get('zone');
			let palette;
			switch (zone){
				case "urban":
				palette = this.colorscaleUrban;
				break;
				case "rural":
				palette= this.colorscaleRural;
				break;
				default:
				palette = this.colorscaleUrban;
			}
			const d = feature.get('distance_overtaker_median');
			color = palette.rgba(d)	
		} else {
			color = this.colorInvalid;
		}

		const w = this.resolutionToNearMidFar(resolution);

		const alpha = 1.0 * w[0] + 0.5 * w[1] + 0.5 * w[2];
		const width = ((selected|hovered) ? 4.0 : 2.0) * w[0] + 4 * w[1] + 200.0 / resolution * w[2];

		color[3] = alpha;

		const style = new ol.style.Style({
			stroke: new ol.style.Stroke({
				color: color,
				width: width,
			})
		});
		return style;
	}

}



class RoadStyle_MinimumDistance extends FeatureStyle{
	constructor(){
		super();
		this.colorInvalid = [0, 0, 0, 255];

		this.colorscaleUrban = new Colorscale([
			[0.0000, [ 64,   0,   0]],
			[1.4999, [196,   0,   0]],
			[1.5000, [196, 196,   0]],
			[2.0000, [  0, 196,   0]],
			[2.5500, [  0, 255,   0]]
		], [128, 128, 128]);
		
		this.colorscaleRural = new Colorscale([
			[0.0000, [ 64,   0,   0]],
			[1.9999, [196,   0,   0]],
			[2.0000, [196, 196,   0]],
			[2.5000, [  0, 196,   0]],
			[2.5500, [  0, 255,   0]]
		], [128, 128, 128]);	
	}

	styleFunction(feature, resolution, selected=false, hovered=false){
		const valid = feature.get('valid');

		let color;
		if (valid){
			const zone = feature.get('zone');
			let palette;
			switch (zone){
				case "urban":
				palette = this.colorscaleUrban;
				break;
				case "rural":
				palette= this.colorscaleRural;
				break;
				default:
				palette = this.colorscaleUrban;
			}
			const d = feature.get('distance_overtaker_minimum');
			color = palette.rgba(d)	
		} else {
			color = this.colorInvalid;
		}

		const w = this.resolutionToNearMidFar(resolution);

		const alpha = 1.0 * w[0] + 0.5 * w[1] + 0.5 * w[2];
		const width = ((selected|hovered) ? 4.0 : 2.0) * w[0] + 4 * w[1] + 200.0 / resolution * w[2];

		color[3] = alpha;

		const style = new ol.style.Style({
			stroke: new ol.style.Stroke({
				color: color,
				width: width,
			})
		});
		return style;
	}

}


